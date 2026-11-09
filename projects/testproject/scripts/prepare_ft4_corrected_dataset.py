#!/usr/bin/env python3
"""Build a corrected FT4 LeRobot v3 dataset view.

Source demonstrations and MP4 files remain immutable. The derivative rewrites
aligned parquet rows and episode timestamps, keeps the exact recorded task
instruction, and removes only reviewed static or human setup before movement.
It deliberately avoids truncated focus episodes because PI05 trains on a
50-action target and does not mask episode-end padding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

FPS = 30
ORANGE_SOURCE = Path("/home/gaikwad-prakash/orange_grasp_corrective_ft4_20261108")
MATCHBOX_SOURCE = Path("/home/gaikwad-prakash/matchbox_pickplace_ft4_20261108")
OUTPUT_ROOT = Path("/home/gaikwad-prakash/ft4_corrected_20261110")
DEPLOYED_ORANGE_TASK = "pick up the orange and place it on the plate"
MATCHBOX_TASK = "pick up the matchbox and place it on the plate"
ORANGE_ACCEPTED = list(range(1, 31))
ORANGE_VALIDATION = [1, 7, 18, 24, 30]
MATCHBOX_VALIDATION = [4]
OPENING_LEAD_FRAMES = 5
# Diagnostic boundary only; no truncated focus episodes are materialized.
FOCUS_POST_CLOSE_FRAMES = 120
CAMERAS = ("observation.images.front", "observation.images.wrist")


@dataclass(frozen=True)
class OutputEpisode:
    source_kind: str
    source_episode: int
    start: int
    stop: int
    task: str
    task_index: int
    kind: str

    @property
    def length(self) -> int:
        return self.stop - self.start


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_all(root: Path, subtree: str) -> pd.DataFrame:
    paths = sorted((root / subtree).glob("**/*.parquet"))
    if not paths:
        raise RuntimeError(f"No parquet files under {root / subtree}")
    return pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)


def source_bundle(root: Path) -> dict:
    return {
        "root": root,
        "data": read_all(root, "data").sort_values("index").reset_index(drop=True),
        "episodes": read_all(root, "meta/episodes")
        .sort_values("episode_index")
        .reset_index(drop=True),
        "info": json.loads((root / "meta/info.json").read_text()),
        "stats": json.loads((root / "meta/stats.json").read_text()),
    }


def source_episode(bundle: dict, episode: int) -> tuple[pd.DataFrame, pd.Series]:
    matches = bundle["episodes"][bundle["episodes"]["episode_index"] == episode]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one metadata row for episode {episode}, got {len(matches)}")
    meta = matches.iloc[0]
    rows = bundle["data"][bundle["data"]["episode_index"] == episode].copy()
    rows = rows.sort_values("frame_index").reset_index(drop=True)
    if len(rows) != int(meta["length"]):
        raise RuntimeError(f"Episode {episode} data/metadata length mismatch")
    if not np.array_equal(rows["frame_index"].to_numpy(), np.arange(len(rows))):
        raise RuntimeError(f"Episode {episode} frame indices are not contiguous")
    return rows, meta


def find_boundaries(rows: pd.DataFrame) -> dict:
    actions = np.stack(rows["action"].to_numpy()).astype(np.float32)
    start = np.median(actions[:10], axis=0)
    motion_score = np.max(np.abs(actions[:, :5] - start[:5]), axis=1)
    motion_indices = np.flatnonzero(motion_score >= 3.0)
    if not len(motion_indices):
        raise RuntimeError("No >=3 degree arm motion found")
    motion = int(motion_indices[0])
    trim_start = max(0, motion - OPENING_LEAD_FRAMES)

    gripper = actions[:, 5]
    one_second_change = gripper[30:] - gripper[:-30]
    search_start = max(trim_start, motion)
    close_start = search_start + int(np.argmin(one_second_change[search_start:]))
    close_drop = float(one_second_change[close_start])
    if close_drop > -7.0:
        raise RuntimeError(f"No meaningful close found; strongest 1 s change={close_drop:.3f}")
    focus_stop = min(len(actions), close_start + FOCUS_POST_CLOSE_FRAMES)
    if focus_stop - trim_start < 60:
        raise RuntimeError("Focus window is unexpectedly short")
    return {
        "source_frames": len(actions),
        "motion_frame": motion,
        "trim_start": trim_start,
        "removed_opening_frames": trim_start,
        "close_start": close_start,
        "close_drop_deg_per_s": close_drop,
        "focus_stop_exclusive": focus_stop,
        "full_frames": len(actions) - trim_start,
        "focus_frames": focus_stop - trim_start,
    }


def numeric_stats(values: np.ndarray) -> dict[str, list]:
    values = np.asarray(values)
    return {
        "min": np.min(values, axis=0).astype(float).tolist(),
        "max": np.max(values, axis=0).astype(float).tolist(),
        "mean": np.mean(values, axis=0).astype(float).tolist(),
        "std": np.std(values, axis=0).astype(float).tolist(),
        "count": [int(values.shape[0])],
        "q01": np.quantile(values, 0.01, axis=0).astype(float).tolist(),
        "q10": np.quantile(values, 0.10, axis=0).astype(float).tolist(),
        "q50": np.quantile(values, 0.50, axis=0).astype(float).tolist(),
        "q90": np.quantile(values, 0.90, axis=0).astype(float).tolist(),
        "q99": np.quantile(values, 0.99, axis=0).astype(float).tolist(),
    }


def scalar_stats(values: np.ndarray) -> dict[str, list]:
    stats = numeric_stats(np.asarray(values).reshape(-1, 1))
    return {key: [value[0]] if key != "count" else value for key, value in stats.items()}


def update_numeric_stats(base: dict, data: pd.DataFrame) -> dict:
    output = dict(base)
    output["action"] = numeric_stats(np.stack(data["action"].to_numpy()))
    output["observation.state"] = numeric_stats(np.stack(data["observation.state"].to_numpy()))
    for key in ("timestamp", "frame_index", "episode_index", "index", "task_index"):
        output[key] = scalar_stats(data[key].to_numpy())
    return output


def update_episode_stats(meta: pd.Series, selected: pd.DataFrame) -> pd.Series:
    output = meta.copy()
    features = {
        "action": numeric_stats(np.stack(selected["action"].to_numpy())),
        "observation.state": numeric_stats(np.stack(selected["observation.state"].to_numpy())),
    }
    for key in ("timestamp", "frame_index", "episode_index", "index", "task_index"):
        features[key] = scalar_stats(selected[key].to_numpy())
    for feature, stats in features.items():
        for stat, value in stats.items():
            output[f"stats/{feature}/{stat}"] = value
    return output


def video_file_count(root: Path, camera: str) -> int:
    return len(list((root / "videos" / camera).glob("**/*.mp4")))


def link_videos(output_root: Path, bundles: dict[str, dict], matchbox_offset: int) -> None:
    for camera in CAMERAS:
        destination = output_root / "videos" / camera / "chunk-000"
        destination.mkdir(parents=True, exist_ok=True)
        for kind, offset in (("orange", 0), ("matchbox", matchbox_offset)):
            files = sorted((bundles[kind]["root"] / "videos" / camera).glob("**/*.mp4"))
            for path in files:
                source_index = int(path.stem.split("-")[-1])
                shared = output_root.parent / "source_videos" / kind / camera / "chunk-000" / path.name
                shared.parent.mkdir(parents=True, exist_ok=True)
                if not shared.exists():
                    shared.hardlink_to(path.resolve())
                target = destination / f"file-{source_index + offset:03d}.mp4"
                target.symlink_to(os.path.relpath(shared, start=destination))


def build_specs(plan: dict, bundles: dict[str, dict]) -> tuple[list[OutputEpisode], list[OutputEpisode]]:
    train: list[OutputEpisode] = []
    validation: list[OutputEpisode] = []
    orange_train = [episode for episode in ORANGE_ACCEPTED if episode not in ORANGE_VALIDATION]
    for episode in orange_train:
        length = len(source_episode(bundles["orange"], episode)[0])
        train.append(OutputEpisode("orange", episode, plan["orange"][episode]["trim_start"], length,
                                   DEPLOYED_ORANGE_TASK, 0, "trimmed_full"))
    for episode in range(5):
        length = len(source_episode(bundles["matchbox"], episode)[0])
        spec = OutputEpisode("matchbox", episode, plan["matchbox"][episode]["trim_start"], length,
                             MATCHBOX_TASK, 1, "trimmed_full")
        (validation if episode in MATCHBOX_VALIDATION else train).append(spec)
    for episode in ORANGE_VALIDATION:
        length = len(source_episode(bundles["orange"], episode)[0])
        validation.append(OutputEpisode("orange", episode, plan["orange"][episode]["trim_start"], length,
                                        DEPLOYED_ORANGE_TASK, 0, "trimmed_full"))
    return train, validation


def materialize_view(
    output_root: Path,
    repo_id: str,
    specs: list[OutputEpisode],
    bundles: dict[str, dict],
    matchbox_video_offset: int,
) -> dict:
    (output_root / "data/chunk-000").mkdir(parents=True)
    (output_root / "meta/episodes/chunk-000").mkdir(parents=True)
    rows: list[pd.DataFrame] = []
    episode_rows: list[pd.Series] = []
    mapping: list[dict] = []
    global_index = 0

    for output_episode, spec in enumerate(specs):
        source_rows, source_meta = source_episode(bundles[spec.source_kind], spec.source_episode)
        selected = source_rows.iloc[spec.start : spec.stop].copy().reset_index(drop=True)
        selected["timestamp"] = np.arange(spec.length, dtype=np.float32) / FPS
        selected["frame_index"] = np.arange(spec.length, dtype=np.int64)
        selected["episode_index"] = output_episode
        selected["index"] = np.arange(global_index, global_index + spec.length, dtype=np.int64)
        selected["task_index"] = spec.task_index

        meta = source_meta.copy()
        meta["episode_index"] = output_episode
        meta["tasks"] = [spec.task]
        meta["length"] = spec.length
        meta["data/chunk_index"] = 0
        meta["data/file_index"] = 0
        meta["dataset_from_index"] = global_index
        meta["dataset_to_index"] = global_index + spec.length
        meta["meta/episodes/chunk_index"] = 0
        meta["meta/episodes/file_index"] = 0
        video_offset = matchbox_video_offset if spec.source_kind == "matchbox" else 0
        for camera in CAMERAS:
            prefix = f"videos/{camera}"
            meta[f"{prefix}/chunk_index"] = 0
            meta[f"{prefix}/file_index"] = int(source_meta[f"{prefix}/file_index"]) + video_offset
            source_from = float(source_meta[f"{prefix}/from_timestamp"])
            meta[f"{prefix}/from_timestamp"] = source_from + spec.start / FPS
            meta[f"{prefix}/to_timestamp"] = source_from + spec.stop / FPS
        meta = update_episode_stats(meta, selected)

        rows.append(selected)
        episode_rows.append(meta)
        mapping.append({
            "output_episode": output_episode,
            "source_kind": spec.source_kind,
            "source_episode": spec.source_episode,
            "source_start_frame": spec.start,
            "source_stop_exclusive": spec.stop,
            "frames": spec.length,
            "kind": spec.kind,
            "task": spec.task,
        })
        global_index += spec.length

    data = pd.concat(rows, ignore_index=True)
    episodes = pd.DataFrame(episode_rows).reset_index(drop=True)
    data.to_parquet(output_root / "data/chunk-000/file-000.parquet", index=False)
    episodes.to_parquet(output_root / "meta/episodes/chunk-000/file-000.parquet", index=False)
    pd.DataFrame(mapping).to_csv(output_root / "meta/source_mapping.csv", index=False)
    pd.DataFrame(
        {"task_index": [0, 1]},
        index=pd.Index([DEPLOYED_ORANGE_TASK, MATCHBOX_TASK], name="task"),
    ).to_parquet(output_root / "meta/tasks.parquet")

    info = dict(bundles["orange"]["info"])
    info["total_episodes"] = len(episodes)
    info["total_frames"] = len(data)
    info["total_tasks"] = 2
    info["data_files_size_in_mb"] = max(
        100, int((output_root / "data/chunk-000/file-000.parquet").stat().st_size / 1e6) + 1
    )
    info["video_files_size_in_mb"] = 200
    info["splits"] = {"train": f"0:{len(episodes)}"}
    (output_root / "meta/info.json").write_text(json.dumps(info, indent=2) + "\n")
    (output_root / "meta/stats.json").write_text(
        json.dumps(update_numeric_stats(bundles["orange"]["stats"], data), indent=2) + "\n"
    )
    link_videos(output_root, bundles, matchbox_video_offset)
    return {
        "root": str(output_root),
        "repo_id": repo_id,
        "episodes": len(episodes),
        "frames": len(data),
        "mapping": mapping,
    }


def summarize_plan(plan: dict) -> dict:
    output = {}
    for kind, episodes in plan.items():
        rows = list(episodes.values())
        output[kind] = {
            "episodes": len(rows),
            "removed_opening_frames": int(sum(row["removed_opening_frames"] for row in rows)),
            "removed_opening_seconds": round(
                sum(row["removed_opening_frames"] for row in rows) / FPS, 3
            ),
            "trim_start_frames": {
                "min": min(row["trim_start"] for row in rows),
                "median": float(np.median([row["trim_start"] for row in rows])),
                "max": max(row["trim_start"] for row in rows),
            },
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "projects/testproject/results/so101_bench_20261019/"
            "ft4_corrected_dataset_20261110/manifest.json"
        ),
    )
    args = parser.parse_args()

    bundles = {
        "orange": source_bundle(ORANGE_SOURCE),
        "matchbox": source_bundle(MATCHBOX_SOURCE),
    }
    plan = {"orange": {}, "matchbox": {}}
    for episode in ORANGE_ACCEPTED:
        plan["orange"][episode] = find_boundaries(source_episode(bundles["orange"], episode)[0])
    for episode in range(5):
        plan["matchbox"][episode] = find_boundaries(
            source_episode(bundles["matchbox"], episode)[0]
        )
    train_specs, validation_specs = build_specs(plan, bundles)

    if OUTPUT_ROOT.exists() and not args.dry_run:
        if not args.rebuild:
            raise SystemExit(f"Output exists: {OUTPUT_ROOT}; pass --rebuild to replace the derivative")
        shutil.rmtree(OUTPUT_ROOT)

    materialized = None
    if not args.dry_run:
        matchbox_offset = video_file_count(ORANGE_SOURCE, CAMERAS[0])
        materialized = {
            "train": materialize_view(
                OUTPUT_ROOT / "train29",
                "local/ft4_corrected_train29_20261110",
                train_specs,
                bundles,
                matchbox_offset,
            ),
            "validation": materialize_view(
                OUTPUT_ROOT / "val6",
                "local/ft4_corrected_val6_20261110",
                validation_specs,
                bundles,
                matchbox_offset,
            ),
        }

    manifest = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "planned" if args.dry_run else "materialized",
        "sources_preserved": True,
        "source_roots": {kind: str(bundle["root"]) for kind, bundle in bundles.items()},
        "source_hashes": {
            kind: sha256(bundle["root"] / "meta/info.json") for kind, bundle in bundles.items()
        },
        "deployed_orange_task": DEPLOYED_ORANGE_TASK,
        "opening_rule": {
            "motion_threshold_deg": 3.0,
            "lead_frames_retained": OPENING_LEAD_FRAMES,
            "reason": (
                "Keep five start-pose frames immediately before meaningful expert motion; "
                "exclude earlier static or human object-placement setup frames."
            ),
        },
        "phase_weighting": {
            "method": "none",
            "reason": (
                "Truncated focus episodes were rejected before training because PI05's 50-action "
                "loss does not mask episode-end padding. All retained entries end at the natural "
                "recorded episode boundary."
            ),
        },
        "split": {
            "orange_train_source_episodes": [
                episode for episode in ORANGE_ACCEPTED if episode not in ORANGE_VALIDATION
            ],
            "orange_validation_source_episodes": ORANGE_VALIDATION,
            "matchbox_train_source_episodes": [0, 1, 2, 3],
            "matchbox_validation_source_episodes": MATCHBOX_VALIDATION,
        },
        "summary": summarize_plan(plan),
        "boundaries": {
            kind: {str(episode): values for episode, values in episodes.items()}
            for kind, episodes in plan.items()
        },
        "image_stats_note": (
            "Camera pixels are exact source MP4 frames. Image summary stats are inherited; "
            "PI05 training uses use_imagenet_stats=false."
        ),
        "materialized": materialized,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "summary": manifest["summary"],
                "train_plan": {
                    "episodes": len(train_specs),
                    "frames": sum(spec.length for spec in train_specs),
                },
                "validation_plan": {
                    "episodes": len(validation_specs),
                    "frames": sum(spec.length for spec in validation_specs),
                },
                "materialized": materialized,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
