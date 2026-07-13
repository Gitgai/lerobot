#!/usr/bin/env python3
"""Create a fast action-start-trimmed LeRobot dataset view.

This avoids slow image/video re-encoding. It trims the tabular rows and episode
metadata, then reuses the existing cleaned dataset videos by pointing each
episode to later timestamps inside the same video files.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


FPS = 30
TASK_TEXT = "pick up the orange and move it to another place"

SOURCE_ROOT = Path("/data/lerobot_datasets/so101_pick_orange_move_cleaned")
OUTPUT_ROOT = Path("/data/lerobot_datasets/so101_pick_orange_move_action_start_view")
REPO_ID = "local/so101_pick_orange_move_action_start_view"

# Flattened global episode indices from:
# batch01 ep0-9, batch02 ep0-9, batch03 ep0-9.
TRIM_START_SECONDS = {
    0: 3.05,
    1: 2.62,
    2: 4.65,
    3: 3.68,
    4: 4.78,
    5: 3.98,
    6: 3.72,
    7: 2.85,
    8: 4.08,
    9: 3.55,
    10: 2.08,
    11: 2.42,
    12: 3.45,
    13: 2.52,
    14: 1.92,
    15: 2.18,
    16: 2.45,
    17: 2.32,
    18: 3.12,
    19: 2.85,
    20: 0.0,
    21: 1.68,
    22: 1.98,
    23: 3.05,
    24: 1.95,
    25: 1.82,
    26: 1.88,
    27: 2.15,
    28: 1.65,
    29: 3.88,
}


def to_list(array: np.ndarray) -> list:
    return array.astype(float).tolist()


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
    stats = numeric_stats(values.reshape(-1, 1))
    return {key: [value[0]] if key != "count" else value for key, value in stats.items()}


def update_stats(stats: dict, data: pd.DataFrame) -> dict:
    updated = dict(stats)
    updated["action"] = numeric_stats(np.stack(data["action"].to_numpy()))
    updated["observation.state"] = numeric_stats(np.stack(data["observation.state"].to_numpy()))
    for key in ["timestamp", "frame_index", "episode_index", "index", "task_index"]:
        updated[key] = scalar_stats(data[key].to_numpy())
    return updated


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)

    (OUTPUT_ROOT / "data/chunk-000").mkdir(parents=True)
    (OUTPUT_ROOT / "meta/episodes/chunk-000").mkdir(parents=True)
    (OUTPUT_ROOT / "videos").mkdir(parents=True)

    source_data = pd.read_parquet(SOURCE_ROOT / "data/chunk-000/file-000.parquet")
    source_eps = pd.read_parquet(SOURCE_ROOT / "meta/episodes/chunk-000/file-000.parquet")

    rows = []
    episode_rows = []
    dataset_index = 0

    for _, ep_row in source_eps.sort_values("episode_index").iterrows():
        ep = int(ep_row["episode_index"])
        source_from = int(ep_row["dataset_from_index"])
        source_to = int(ep_row["dataset_to_index"])
        source_length = source_to - source_from
        start_frame = int(np.floor(TRIM_START_SECONDS[ep] * FPS))
        start_frame = max(0, min(start_frame, source_length - 1))

        selected = source_data.iloc[source_from + start_frame : source_to].copy()
        new_length = len(selected)
        selected["timestamp"] = np.arange(new_length, dtype=np.float32) / FPS
        selected["frame_index"] = np.arange(new_length, dtype=np.int64)
        selected["episode_index"] = ep
        selected["index"] = np.arange(dataset_index, dataset_index + new_length, dtype=np.int64)
        selected["task_index"] = 0
        rows.append(selected)

        new_ep = ep_row.copy()
        new_ep["length"] = new_length
        new_ep["tasks"] = [TASK_TEXT]
        new_ep["dataset_from_index"] = dataset_index
        new_ep["dataset_to_index"] = dataset_index + new_length
        for camera_key in [
            "observation.images.front",
            "observation.images.top",
            "observation.images.wrist",
        ]:
            from_key = f"videos/{camera_key}/from_timestamp"
            new_ep[from_key] = float(ep_row[from_key]) + (start_frame / FPS)
            # Keep the original to_timestamp because the previous cleaned dataset
            # already removed the rest/extra tail.
        episode_rows.append(new_ep)
        dataset_index += new_length

        print(
            f"ep{ep:02d}: drop_start_frames={start_frame:3d} "
            f"old_len={source_length:4d} new_len={new_length:4d}"
        )

    data = pd.concat(rows, ignore_index=True)
    episodes = pd.DataFrame(episode_rows).reset_index(drop=True)

    data.to_parquet(OUTPUT_ROOT / "data/chunk-000/file-000.parquet")
    episodes.to_parquet(OUTPUT_ROOT / "meta/episodes/chunk-000/file-000.parquet")

    shutil.copy2(SOURCE_ROOT / "meta/tasks.parquet", OUTPUT_ROOT / "meta/tasks.parquet")

    info = json.loads((SOURCE_ROOT / "meta/info.json").read_text())
    info["repo_id"] = REPO_ID
    info["total_frames"] = int(len(data))
    info["total_episodes"] = int(episodes["episode_index"].nunique())
    info["total_videos"] = 3
    (OUTPUT_ROOT / "meta/info.json").write_text(json.dumps(info, indent=2) + "\n")

    stats = json.loads((SOURCE_ROOT / "meta/stats.json").read_text())
    (OUTPUT_ROOT / "meta/stats.json").write_text(json.dumps(update_stats(stats, data), indent=2) + "\n")

    # Reuse existing encoded video files without re-encoding. The episode metadata
    # timestamps above point to the later start time inside these same videos.
    for camera_key in [
        "observation.images.front",
        "observation.images.top",
        "observation.images.wrist",
    ]:
        src_dir = SOURCE_ROOT / "videos" / camera_key
        dst_dir = OUTPUT_ROOT / "videos" / camera_key
        dst_dir.parent.mkdir(parents=True, exist_ok=True)
        dst_dir.symlink_to(src_dir, target_is_directory=True)

    print()
    print("ACTION_START_VIEW_DATASET_OK")
    print(f"root: {OUTPUT_ROOT}")
    print(f"repo_id: {REPO_ID}")
    print(f"frames: {len(data)}")
    print(f"episodes: {episodes['episode_index'].nunique()}")


if __name__ == "__main__":
    main()
