#!/usr/bin/env python3
"""Create a focused grasp/pick/move LeRobot dataset view.

This script uses the reviewed grasp-window CSV to build a new LeRobot v3
dataset from the existing SO-101 orange dataset. It does not modify the source
dataset and it does not move the robot.

The output keeps video-backed camera features by reusing the original MP4 files
through symlinks, while the new episode metadata points each focused episode at
the approved timestamp window inside those videos.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

FPS = 30
TASK_TEXT = "pick up the orange and move it to another place"
DEFAULT_SOURCE_ROOT = Path("/data/lerobot_datasets/so101_orange_49")
DEFAULT_REVIEW_CSV = Path(
    "projects/testproject/artifacts/dataset_grasp_window_audit_20260720/grasp_pick_move_review.csv"
)
DEFAULT_OUTPUT_ROOT = Path("/data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus")
DEFAULT_REPO_ID = "local/so101_orange_49_grasp_pick_move_focus"

CAMERA_KEYS = [
    "observation.images.front",
    "observation.images.top",
    "observation.images.wrist",
]


@dataclass(frozen=True)
class FocusWindow:
    new_episode_index: int
    source_episode_index: int
    source_start_frame: int
    source_end_frame: int
    label: str
    holdout: bool
    reason: str
    notes: str

    @property
    def length(self) -> int:
        return self.source_end_frame - self.source_start_frame + 1


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(["1", "true", "yes", "y"])


def to_list(array: np.ndarray) -> list:
    return np.asarray(array).astype(float).tolist()


def numeric_stats(values: np.ndarray) -> dict[str, list]:
    values = np.asarray(values)
    return {
        "min": to_list(np.min(values, axis=0)),
        "max": to_list(np.max(values, axis=0)),
        "mean": to_list(np.mean(values, axis=0)),
        "std": to_list(np.std(values, axis=0)),
        "count": [int(values.shape[0])],
        "q01": to_list(np.quantile(values, 0.01, axis=0)),
        "q10": to_list(np.quantile(values, 0.10, axis=0)),
        "q50": to_list(np.quantile(values, 0.50, axis=0)),
        "q90": to_list(np.quantile(values, 0.90, axis=0)),
        "q99": to_list(np.quantile(values, 0.99, axis=0)),
    }


def scalar_stats(values: np.ndarray) -> dict[str, list]:
    stats = numeric_stats(np.asarray(values).reshape(-1, 1))
    return {key: [value[0]] if key != "count" else value for key, value in stats.items()}


def update_global_stats(source_stats: dict, data: pd.DataFrame) -> dict:
    updated = dict(source_stats)
    updated["action"] = numeric_stats(np.stack(data["action"].to_numpy()))
    updated["observation.state"] = numeric_stats(np.stack(data["observation.state"].to_numpy()))
    for key in ["timestamp", "frame_index", "episode_index", "index", "task_index"]:
        updated[key] = scalar_stats(data[key].to_numpy())
    return updated


def episode_numeric_stats(data: pd.DataFrame) -> dict[str, dict[str, list]]:
    stats = {
        "action": numeric_stats(np.stack(data["action"].to_numpy())),
        "observation.state": numeric_stats(np.stack(data["observation.state"].to_numpy())),
    }
    for key in ["timestamp", "frame_index", "episode_index", "index", "task_index"]:
        stats[key] = scalar_stats(data[key].to_numpy())
    return stats


def load_windows(review_csv: Path, include_holdout: bool) -> list[FocusWindow]:
    review = pd.read_csv(review_csv)
    holdout = _as_bool(review["holdout"])
    selected = review[review["label"].eq("good")].copy()
    if not include_holdout:
        selected = selected[~holdout.loc[selected.index]]
    selected = selected.sort_values("episode_index").reset_index(drop=True)

    windows: list[FocusWindow] = []
    for new_ep, row in selected.iterrows():
        start = int(row["approved_start_frame"])
        end = int(row["approved_end_frame"])
        if end < start:
            raise ValueError(
                f"Invalid approved window for source episode {row['episode_index']}: {start}>{end}"
            )
        windows.append(
            FocusWindow(
                new_episode_index=int(new_ep),
                source_episode_index=int(row["episode_index"]),
                source_start_frame=start,
                source_end_frame=end,
                label=str(row["label"]),
                holdout=bool(_as_bool(pd.Series([row["holdout"]])).iloc[0]),
                reason=str(row.get("reason", "")),
                notes=str(row.get("notes", "")),
            )
        )
    return windows


def make_episode_row(
    *,
    source_ep: pd.Series,
    selected_data: pd.DataFrame,
    window: FocusWindow,
    dataset_from_index: int,
) -> pd.Series:
    new_ep = source_ep.copy()
    new_ep["episode_index"] = window.new_episode_index
    new_ep["tasks"] = [TASK_TEXT]
    new_ep["length"] = window.length
    new_ep["data/chunk_index"] = 0
    new_ep["data/file_index"] = 0
    new_ep["dataset_from_index"] = dataset_from_index
    new_ep["dataset_to_index"] = dataset_from_index + window.length
    new_ep["meta/episodes/chunk_index"] = 0
    new_ep["meta/episodes/file_index"] = 0

    for camera_key in CAMERA_KEYS:
        from_key = f"videos/{camera_key}/from_timestamp"
        to_key = f"videos/{camera_key}/to_timestamp"
        source_from = float(source_ep[from_key])
        new_ep[from_key] = source_from + window.source_start_frame / FPS
        new_ep[to_key] = source_from + (window.source_end_frame + 1) / FPS

    stats = episode_numeric_stats(selected_data)
    for feature, feature_stats in stats.items():
        for stat_name, value in feature_stats.items():
            new_ep[f"stats/{feature}/{stat_name}"] = value

    return new_ep


def build_dataset(
    *,
    source_root: Path,
    review_csv: Path,
    output_root: Path,
    repo_id: str,
    include_holdout: bool,
    overwrite: bool,
    dry_run: bool,
) -> None:
    if output_root.resolve() == source_root.resolve():
        raise ValueError("Refusing to overwrite the source dataset.")
    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"{output_root} already exists. Use --overwrite to replace it.")
        if dry_run:
            print(f"dry_run_would_remove_existing_output: {output_root}")
        else:
            shutil.rmtree(output_root)

    windows = load_windows(review_csv, include_holdout=include_holdout)
    source_data = pd.read_parquet(source_root / "data/chunk-000/file-000.parquet")
    source_eps = pd.read_parquet(source_root / "meta/episodes/chunk-000/file-000.parquet")

    print("GRASP/PICK/MOVE FOCUS DATASET PLAN")
    print(f"source_root: {source_root}")
    print(f"review_csv: {review_csv}")
    print(f"output_root: {output_root}")
    print(f"repo_id: {repo_id}")
    print(f"include_holdout: {include_holdout}")
    print(f"windows: {len(windows)}")
    print(f"frames: {sum(window.length for window in windows)}")
    print()
    print("new_ep source_ep start end frames")
    print("-" * 40)
    for window in windows:
        print(
            f"{window.new_episode_index:>6} {window.source_episode_index:>9} "
            f"{window.source_start_frame:>5} {window.source_end_frame:>5} {window.length:>6}"
        )

    if dry_run:
        print()
        print("DRY_RUN_OK: no files written.")
        return

    (output_root / "data/chunk-000").mkdir(parents=True)
    (output_root / "meta/episodes/chunk-000").mkdir(parents=True)
    (output_root / "videos").mkdir(parents=True)

    rows: list[pd.DataFrame] = []
    episode_rows: list[pd.Series] = []
    mapping_rows: list[dict] = []
    dataset_index = 0

    for window in windows:
        ep_matches = source_eps[source_eps["episode_index"] == window.source_episode_index]
        if ep_matches.empty:
            raise ValueError(f"Source episode {window.source_episode_index} not found")
        source_ep = ep_matches.iloc[0]
        source_from = int(source_ep["dataset_from_index"])
        source_to = int(source_ep["dataset_to_index"])
        source_length = source_to - source_from
        if window.source_end_frame >= source_length:
            raise ValueError(
                f"Window {window.source_episode_index} ends at {window.source_end_frame}, "
                f"but source length is {source_length}"
            )

        selected = source_data.iloc[
            source_from + window.source_start_frame : source_from + window.source_end_frame + 1
        ].copy()
        if len(selected) != window.length:
            raise RuntimeError(
                f"Window length mismatch for source episode {window.source_episode_index}: "
                f"expected {window.length}, got {len(selected)}"
            )

        selected["timestamp"] = np.arange(window.length, dtype=np.float32) / FPS
        selected["frame_index"] = np.arange(window.length, dtype=np.int64)
        selected["episode_index"] = window.new_episode_index
        selected["index"] = np.arange(dataset_index, dataset_index + window.length, dtype=np.int64)
        selected["task_index"] = 0
        rows.append(selected)

        episode_rows.append(
            make_episode_row(
                source_ep=source_ep,
                selected_data=selected,
                window=window,
                dataset_from_index=dataset_index,
            )
        )
        mapping_rows.append(
            {
                "new_episode_index": window.new_episode_index,
                "source_episode_index": window.source_episode_index,
                "source_start_frame": window.source_start_frame,
                "source_end_frame": window.source_end_frame,
                "length": window.length,
                "source_global_start_index": source_from + window.source_start_frame,
                "source_global_end_index": source_from + window.source_end_frame,
                "holdout": window.holdout,
                "label": window.label,
                "reason": window.reason,
                "notes": window.notes,
            }
        )
        dataset_index += window.length

    data = pd.concat(rows, ignore_index=True)
    episodes = pd.DataFrame(episode_rows).reset_index(drop=True)
    mapping = pd.DataFrame(mapping_rows)

    data.to_parquet(output_root / "data/chunk-000/file-000.parquet")
    episodes.to_parquet(output_root / "meta/episodes/chunk-000/file-000.parquet")
    mapping.to_csv(output_root / "meta/grasp_focus_windows.csv", index=False)

    shutil.copy2(source_root / "meta/tasks.parquet", output_root / "meta/tasks.parquet")

    info = json.loads((source_root / "meta/info.json").read_text())
    # Keep info.json compatible with LeRobot's DatasetInfo schema. The repo id
    # is passed to LeRobotDataset/lerobot-train separately.
    info.pop("repo_id", None)
    info.pop("total_videos", None)
    info["total_frames"] = int(len(data))
    info["total_episodes"] = int(len(episodes))
    info["total_tasks"] = 1
    info["splits"] = {"train": f"0:{len(episodes)}"}
    (output_root / "meta/info.json").write_text(json.dumps(info, indent=2) + "\n")

    source_stats = json.loads((source_root / "meta/stats.json").read_text())
    (output_root / "meta/stats.json").write_text(
        json.dumps(update_global_stats(source_stats, data), indent=2) + "\n"
    )

    for camera_key in CAMERA_KEYS:
        source_video_dir = source_root / "videos" / camera_key
        output_video_dir = output_root / "videos" / camera_key
        output_video_dir.parent.mkdir(parents=True, exist_ok=True)
        output_video_dir.symlink_to(source_video_dir, target_is_directory=True)

    print()
    print("GRASP_FOCUS_DATASET_OK")
    print(f"root: {output_root}")
    print(f"repo_id: {repo_id}")
    print(f"episodes: {len(episodes)}")
    print(f"frames: {len(data)}")
    print(f"mapping: {output_root / 'meta/grasp_focus_windows.csv'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--review-csv", type=Path, default=DEFAULT_REVIEW_CSV)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--include-holdout", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    build_dataset(
        source_root=args.source_root,
        review_csv=args.review_csv,
        output_root=args.output_root,
        repo_id=args.repo_id,
        include_holdout=args.include_holdout,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
