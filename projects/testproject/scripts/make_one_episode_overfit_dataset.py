#!/usr/bin/env python3
"""Create a one-episode LeRobot dataset for Pi05 overfit diagnosis.

This copies one selected successful episode into a new image-based dataset.
The source dataset is not modified.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from lerobot.datasets.lerobot_dataset import LeRobotDataset


SOURCE_ROOT = Path("/data/lerobot_datasets/so101_pick_orange_30eps")
SOURCE_REPO_ID = "local/so101_pick_orange_30eps"
DEFAULT_OUTPUT_ROOT = Path("/data/lerobot_datasets/so101_pick_orange_episode29_overfit")
DEFAULT_OUTPUT_REPO_ID = "local/so101_pick_orange_episode29_overfit"
TASK_TEXT = "pick up the orange and move it to another place"

VIDEO_KEYS = [
    "observation.images.front",
    "observation.images.top",
    "observation.images.wrist",
]
DATA_KEYS = ["action", "observation.state", *VIDEO_KEYS]


def frame_to_uint8_hwc(image) -> np.ndarray:
    array = image.permute(1, 2, 0).numpy()
    return (array * 255).clip(0, 255).astype("uint8")


def make_features(source: LeRobotDataset) -> dict:
    features = {key: dict(source.features[key]) for key in DATA_KEYS}
    for key in VIDEO_KEYS:
        features[key] = {
            "dtype": "image",
            "shape": tuple(source.features[key]["shape"]),
            "names": list(source.features[key].get("names", ["height", "width", "channels"])),
        }
    return features


def episode_row(source_root: Path, episode: int) -> pd.Series:
    episodes = pd.read_parquet(source_root / "meta/episodes/chunk-000/file-000.parquet")
    matches = episodes[episodes["episode_index"] == episode]
    if matches.empty:
        raise ValueError(f"Episode {episode} not found in {source_root}")
    return matches.iloc[0]


def build_dataset(
    *,
    source_root: Path,
    source_repo_id: str,
    episode: int,
    output_root: Path,
    output_repo_id: str,
    task: str,
    overwrite: bool,
) -> None:
    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"{output_root} already exists. Use --overwrite to replace it.")
        shutil.rmtree(output_root)

    src = LeRobotDataset(source_repo_id, root=source_root)
    ep = episode_row(source_root, episode)
    start_index = int(ep["dataset_from_index"])
    length = int(ep["length"])
    fps = int(src.fps)
    duration_s = length / fps

    print("ONE-EPISODE OVERFIT DATASET")
    print(f"source_root: {source_root}")
    print(f"source_repo_id: {source_repo_id}")
    print(f"source_episode: {episode}")
    print(f"source_start_index: {start_index}")
    print(f"source_length_frames: {length}")
    print(f"source_duration_s: {duration_s:.2f}")
    print(f"output_root: {output_root}")
    print(f"output_repo_id: {output_repo_id}")
    print(f"task: {task}")
    print()

    dst = LeRobotDataset.create(
        repo_id=output_repo_id,
        root=output_root,
        fps=fps,
        robot_type="so_follower",
        features=make_features(src),
        use_videos=False,
        metadata_buffer_size=1,
    )

    for offset in range(length):
        item = src[start_index + offset]
        frame = {
            "action": item["action"].numpy(),
            "observation.state": item["observation.state"].numpy(),
            "task": task,
        }
        for key in VIDEO_KEYS:
            frame[key] = frame_to_uint8_hwc(item[key])
        dst.add_frame(frame)

        if offset and offset % 100 == 0:
            print(f"copied {offset}/{length} frames")

    dst.save_episode(parallel_encoding=True)
    dst.finalize()

    print()
    print("ONE_EPISODE_DATASET_OK")
    print(f"root: {output_root}")
    print(f"repo_id: {output_repo_id}")
    print(f"episode: {episode}")
    print(f"frames: {length}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--source-repo-id", default=SOURCE_REPO_ID)
    parser.add_argument("--episode", type=int, default=29)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--output-repo-id", default=DEFAULT_OUTPUT_REPO_ID)
    parser.add_argument("--task", default=TASK_TEXT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    build_dataset(
        source_root=args.source_root,
        source_repo_id=args.source_repo_id,
        episode=args.episode,
        output_root=args.output_root,
        output_repo_id=args.output_repo_id,
        task=args.task,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
