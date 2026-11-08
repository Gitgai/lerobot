#!/usr/bin/env python3
"""Audit the accepted fine-tune 4 demonstration episodes.

The script validates LeRobot v3 metadata, frame continuity, two-camera video
decoding, front/wrist timing agreement, and exact duplicate trajectories.  It
does not modify either source dataset.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


CAMERAS = ("observation.images.front", "observation.images.wrist")


def read_episode_metadata(root: Path) -> list[dict]:
    tables = [pq.read_table(path) for path in sorted((root / "meta/episodes").glob("**/*.parquet"))]
    if not tables:
        raise RuntimeError(f"No episode metadata found under {root}")
    return pa.concat_tables(tables).sort_by([("episode_index", "ascending")]).to_pylist()


def read_data(root: Path) -> pa.Table:
    tables = [pq.read_table(path) for path in sorted((root / "data").glob("**/*.parquet"))]
    if not tables:
        raise RuntimeError(f"No data parquet found under {root}")
    return pa.concat_tables(tables)


def video_path(root: Path, camera: str, file_index: int) -> Path:
    return root / "videos" / camera / "chunk-000" / f"file-{file_index:03d}.mp4"


def sample_frame(cap: cv2.VideoCapture, timestamp_s: float) -> np.ndarray:
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_s * 1000.0)
    ok, frame = cap.read()
    if not ok or frame is None:
        raise RuntimeError(f"Could not decode frame at {timestamp_s:.3f}s")
    return frame


def frame_summary(frame: np.ndarray) -> tuple[float, float, np.ndarray]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (64, 48), interpolation=cv2.INTER_AREA)
    return float(gray.mean()), float(gray.std()), small


def canonical_trajectory_hash(table: pa.Table) -> str:
    digest = hashlib.sha256()
    for name in ("action", "observation.state"):
        values = np.asarray(table[name].to_pylist(), dtype=np.float32)
        digest.update(name.encode())
        digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def load_review_rows(path: Path) -> dict[int, dict[str, str]]:
    with path.open(newline="") as handle:
        return {int(row["episode"]): row for row in csv.DictReader(handle)}


def audit_source(spec: dict) -> dict:
    root = Path(spec["root"])
    accepted = set(spec["accepted"])
    review_rows = load_review_rows(Path(spec["review_csv"]))
    info = json.loads((root / "meta/info.json").read_text())
    episode_meta = read_episode_metadata(root)
    table = read_data(root)

    errors: list[str] = []
    warnings: list[str] = []
    episode_results: list[dict] = []
    trajectory_hashes: dict[int, str] = {}

    metadata_indices = [int(row["episode_index"]) for row in episode_meta]
    if metadata_indices != list(range(info["total_episodes"])):
        errors.append(f"metadata episode indices are not contiguous: {metadata_indices}")
    if table.num_rows != info["total_frames"]:
        errors.append(f"frame total mismatch: parquet={table.num_rows}, info={info['total_frames']}")

    frame_episode_indices = np.asarray(table["episode_index"].to_numpy(), dtype=np.int64)
    global_indices = np.asarray(table["index"].to_numpy(), dtype=np.int64)
    if not np.array_equal(global_indices, np.arange(len(global_indices), dtype=np.int64)):
        errors.append("global frame indices are not contiguous")

    for row in episode_meta:
        episode = int(row["episode_index"])
        if episode not in accepted:
            continue
        ep_mask = frame_episode_indices == episode
        ep_table = table.filter(pa.array(ep_mask))
        expected_length = int(row["length"])
        ep_errors: list[str] = []
        camera_results: dict[str, dict] = {}

        if ep_table.num_rows != expected_length:
            ep_errors.append(f"length mismatch: data={ep_table.num_rows}, metadata={expected_length}")
        frame_indices = np.asarray(ep_table["frame_index"].to_numpy(), dtype=np.int64)
        if not np.array_equal(frame_indices, np.arange(expected_length, dtype=np.int64)):
            ep_errors.append("frame_index is not contiguous")

        trajectory_hashes[episode] = canonical_trajectory_hash(ep_table)

        intervals = []
        for camera in CAMERAS:
            prefix = f"videos/{camera}"
            file_index = int(row[f"{prefix}/file_index"])
            start = float(row[f"{prefix}/from_timestamp"])
            end = float(row[f"{prefix}/to_timestamp"])
            intervals.append((start, end))
            path = video_path(root, camera, file_index)
            if not path.is_file():
                ep_errors.append(f"missing video: {path}")
                continue

            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                ep_errors.append(f"cannot open video: {path}")
                continue
            width = int(round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
            height = int(round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            duration = max(end - start, 0.0)
            sample_times = [start + duration * fraction for fraction in (0.15, 0.40, 0.65, 0.85)]
            means, stds, samples = [], [], []
            try:
                for timestamp in sample_times:
                    frame = sample_frame(cap, min(timestamp, max(start, end - 1.0 / info["fps"])))
                    mean, std, small = frame_summary(frame)
                    means.append(mean)
                    stds.append(std)
                    samples.append(small)
            except RuntimeError as exc:
                ep_errors.append(f"{camera} decode error: {exc}")
            finally:
                cap.release()

            max_change = 0.0
            if len(samples) > 1:
                max_change = max(
                    float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))))
                    for a, b in zip(samples, samples[1:], strict=False)
                )
            if width != 640 or height != 480:
                ep_errors.append(f"{camera} dimensions are {width}x{height}, expected 640x480")
            if abs(fps - info["fps"]) > 0.25:
                ep_errors.append(f"{camera} fps is {fps:.3f}, expected {info['fps']}")
            if means and (min(means) < 5.0 or min(stds) < 3.0):
                ep_errors.append(f"{camera} contains a blank/flat sampled frame")
            if samples and max_change < 0.5:
                ep_errors.append(f"{camera} sampled frames appear stale (max MAD={max_change:.3f})")
            camera_results[camera] = {
                "file_index": file_index,
                "from_timestamp": start,
                "to_timestamp": end,
                "width": width,
                "height": height,
                "fps": round(fps, 6),
                "sample_mean_min": round(min(means), 3) if means else None,
                "sample_std_min": round(min(stds), 3) if stds else None,
                "sample_max_mad": round(max_change, 3),
            }

        if len(intervals) == 2:
            start_delta = abs(intervals[0][0] - intervals[1][0])
            end_delta = abs(intervals[0][1] - intervals[1][1])
            if start_delta > 1.0 / info["fps"] or end_delta > 1.0 / info["fps"]:
                ep_errors.append(
                    f"front/wrist interval mismatch: start={start_delta:.6f}s end={end_delta:.6f}s"
                )

        review = review_rows.get(episode)
        if not review or review.get("accepted") != "yes":
            ep_errors.append("accepted episode is missing an accepted human-review row")

        errors.extend(f"episode {episode}: {message}" for message in ep_errors)
        episode_results.append(
            {
                "episode": episode,
                "length": expected_length,
                "trajectory_sha256": trajectory_hashes[episode],
                "cameras": camera_results,
                "status": "pass" if not ep_errors else "fail",
                "errors": ep_errors,
            }
        )

    duplicate_groups = [
        sorted(episodes)
        for digest, episodes in _invert_hashes(trajectory_hashes).items()
        if len(episodes) > 1
    ]
    if duplicate_groups:
        errors.append(f"exact duplicate trajectories found: {duplicate_groups}")

    accepted_reviews = {episode for episode, row in review_rows.items() if row.get("accepted") == "yes"}
    if accepted_reviews != accepted:
        errors.append(
            f"accepted set differs from review CSV: spec={sorted(accepted)}, review={sorted(accepted_reviews)}"
        )

    return {
        "name": spec["name"],
        "root": str(root),
        "total_source_episodes": info["total_episodes"],
        "accepted_episodes": sorted(accepted),
        "accepted_count": len(accepted),
        "accepted_frames": int(sum(item["length"] for item in episode_results)),
        "exact_duplicate_groups": duplicate_groups,
        "episode_results": episode_results,
        "warnings": warnings,
        "errors": errors,
        "status": "pass" if not errors else "fail",
    }


def _invert_hashes(hashes: dict[int, str]) -> dict[str, list[int]]:
    output: dict[str, list[int]] = {}
    for episode, digest in hashes.items():
        output.setdefault(digest, []).append(episode)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    sources = [audit_source(source) for source in spec["sources"]]
    all_errors = [f"{source['name']}: {error}" for source in sources for error in source["errors"]]
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "audit_version": 1,
        "spec": str(args.spec.resolve()),
        "status": "pass" if not all_errors else "fail",
        "accepted_episode_count": sum(source["accepted_count"] for source in sources),
        "accepted_frame_count": sum(source["accepted_frames"] for source in sources),
        "sources": sources,
        "errors": all_errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "accepted_episode_count": report["accepted_episode_count"],
        "accepted_frame_count": report["accepted_frame_count"],
        "errors": all_errors,
    }, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
