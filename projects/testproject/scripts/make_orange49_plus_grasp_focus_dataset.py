#!/usr/bin/env python3
"""Create the Option A training dataset: original orange49 + grasp focus.

This is an offline LeRobot v3 dataset view. It concatenates:

1. The original 49 full SO-101 orange episodes.
2. The approved non-holdout grasp/pick/move focused windows, once.

The source datasets are not modified. The output reuses the original MP4 files
through symlinks and updates only parquet rows, episode metadata, and stats.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ORANGE49_ROOT = Path("/data/lerobot_datasets/so101_orange_49")
DEFAULT_FOCUS_ROOT = Path("/data/lerobot_datasets/so101_orange_49_grasp_pick_move_focus")
DEFAULT_OUTPUT_ROOT = Path("/data/lerobot_datasets/so101_orange_49_plus_grasp_pick_move_focus")
DEFAULT_REPO_ID = "local/so101_orange_49_plus_grasp_pick_move_focus"

CAMERA_KEYS = [
    "observation.images.front",
    "observation.images.top",
    "observation.images.wrist",
]


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


def refresh_episode_stats(ep_row: pd.Series, selected_data: pd.DataFrame) -> pd.Series:
    new_ep = ep_row.copy()
    stats = episode_numeric_stats(selected_data)
    for feature, feature_stats in stats.items():
        for stat_name, value in feature_stats.items():
            new_ep[f"stats/{feature}/{stat_name}"] = value
    return new_ep


def build_dataset(
    *,
    orange49_root: Path,
    focus_root: Path,
    output_root: Path,
    repo_id: str,
    overwrite: bool,
    dry_run: bool,
) -> None:
    for source_root in [orange49_root, focus_root]:
        if output_root.resolve() == source_root.resolve():
            raise ValueError(f"Refusing to overwrite source dataset: {source_root}")
    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"{output_root} already exists. Use --overwrite to replace it.")
        if dry_run:
            print(f"dry_run_would_remove_existing_output: {output_root}")
        else:
            shutil.rmtree(output_root)

    orange_data = pd.read_parquet(orange49_root / "data/chunk-000/file-000.parquet")
    orange_eps = pd.read_parquet(orange49_root / "meta/episodes/chunk-000/file-000.parquet")
    focus_data = pd.read_parquet(focus_root / "data/chunk-000/file-000.parquet")
    focus_eps = pd.read_parquet(focus_root / "meta/episodes/chunk-000/file-000.parquet")

    orange_episode_count = int(orange_eps["episode_index"].nunique())
    orange_frame_count = len(orange_data)
    focus_episode_count = int(focus_eps["episode_index"].nunique())
    focus_frame_count = len(focus_data)

    print("ORANGE49 + GRASP FOCUS TRAINING MIX PLAN")
    print(f"orange49_root: {orange49_root}")
    print(f"focus_root: {focus_root}")
    print(f"output_root: {output_root}")
    print(f"repo_id: {repo_id}")
    print(f"orange49 episodes/frames: {orange_episode_count}/{orange_frame_count}")
    print(f"focus episodes/frames: {focus_episode_count}/{focus_frame_count}")
    print(f"output episodes/frames: {orange_episode_count + focus_episode_count}/{orange_frame_count + focus_frame_count}")

    if dry_run:
        print()
        print("DRY_RUN_OK: no files written.")
        return

    (output_root / "data/chunk-000").mkdir(parents=True)
    (output_root / "meta/episodes/chunk-000").mkdir(parents=True)
    (output_root / "videos").mkdir(parents=True)

    orange_data = orange_data.copy()
    orange_data["index"] = np.arange(0, orange_frame_count, dtype=np.int64)

    focus_data = focus_data.copy()
    focus_data["episode_index"] = focus_data["episode_index"].astype(np.int64) + orange_episode_count
    focus_data["index"] = np.arange(
        orange_frame_count, orange_frame_count + focus_frame_count, dtype=np.int64
    )

    merged_data = pd.concat([orange_data, focus_data], ignore_index=True)

    orange_eps = orange_eps.sort_values("episode_index").reset_index(drop=True).copy()
    focus_eps = focus_eps.sort_values("episode_index").reset_index(drop=True).copy()
    focus_eps["episode_index"] = focus_eps["episode_index"].astype(np.int64) + orange_episode_count
    focus_eps["dataset_from_index"] = focus_eps["dataset_from_index"].astype(np.int64) + orange_frame_count
    focus_eps["dataset_to_index"] = focus_eps["dataset_to_index"].astype(np.int64) + orange_frame_count
    focus_eps["data/chunk_index"] = 0
    focus_eps["data/file_index"] = 0
    focus_eps["meta/episodes/chunk_index"] = 0
    focus_eps["meta/episodes/file_index"] = 0

    # Refresh low-dimensional/scalar per-episode stats for the shifted focus
    # rows so episode_index/index stats are correct after concatenation.
    refreshed_focus_rows = []
    for _, ep_row in focus_eps.iterrows():
        start = int(ep_row["dataset_from_index"])
        stop = int(ep_row["dataset_to_index"])
        selected = merged_data.iloc[start:stop]
        refreshed_focus_rows.append(refresh_episode_stats(ep_row, selected))
    focus_eps = pd.DataFrame(refreshed_focus_rows).reset_index(drop=True)

    merged_eps = pd.concat([orange_eps, focus_eps], ignore_index=True)

    merged_data.to_parquet(output_root / "data/chunk-000/file-000.parquet")
    merged_eps.to_parquet(output_root / "meta/episodes/chunk-000/file-000.parquet")

    shutil.copy2(orange49_root / "meta/tasks.parquet", output_root / "meta/tasks.parquet")

    focus_mapping = pd.read_csv(focus_root / "meta/grasp_focus_windows.csv")
    focus_mapping = focus_mapping.copy()
    focus_mapping["new_episode_index_in_training_mix"] = (
        focus_mapping["new_episode_index"].astype(np.int64) + orange_episode_count
    )
    focus_mapping.to_csv(output_root / "meta/grasp_focus_windows.csv", index=False)

    info = json.loads((orange49_root / "meta/info.json").read_text())
    info.pop("repo_id", None)
    info.pop("total_videos", None)
    info["total_frames"] = int(len(merged_data))
    info["total_episodes"] = int(len(merged_eps))
    info["total_tasks"] = 1
    info["splits"] = {"train": f"0:{len(merged_eps)}"}
    (output_root / "meta/info.json").write_text(json.dumps(info, indent=2) + "\n")

    source_stats = json.loads((orange49_root / "meta/stats.json").read_text())
    (output_root / "meta/stats.json").write_text(
        json.dumps(update_global_stats(source_stats, merged_data), indent=2) + "\n"
    )

    for camera_key in CAMERA_KEYS:
        source_video_dir = orange49_root / "videos" / camera_key
        output_video_dir = output_root / "videos" / camera_key
        output_video_dir.parent.mkdir(parents=True, exist_ok=True)
        output_video_dir.symlink_to(source_video_dir, target_is_directory=True)

    print()
    print("ORANGE49_PLUS_GRASP_FOCUS_DATASET_OK")
    print(f"root: {output_root}")
    print(f"repo_id: {repo_id}")
    print(f"episodes: {len(merged_eps)}")
    print(f"frames: {len(merged_data)}")
    print(f"focus_training_episodes: {orange_episode_count}-{len(merged_eps) - 1}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orange49-root", type=Path, default=DEFAULT_ORANGE49_ROOT)
    parser.add_argument("--focus-root", type=Path, default=DEFAULT_FOCUS_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    build_dataset(
        orange49_root=args.orange49_root,
        focus_root=args.focus_root,
        output_root=args.output_root,
        repo_id=args.repo_id,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
