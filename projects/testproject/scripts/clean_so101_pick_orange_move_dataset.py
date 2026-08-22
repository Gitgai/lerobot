#!/usr/bin/env python3
"""Create a cleaned SO-101 orange pick-and-move dataset.

This script reads the three original recording batches, trims each episode using
explicit per-episode start/end times, changes the task text to match the
behavior, and writes a new LeRobot dataset.

Original datasets are never modified.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from lerobot.datasets.lerobot_dataset import LeRobotDataset

TASK_TEXT = "pick up the orange and move it to another place"

BATCH_ROOTS = {
    "batch01": Path("/data/lerobot_datasets/so101_pick_orange_batch01"),
    "batch02": Path("/data/lerobot_datasets/so101_pick_orange_batch02"),
    "batch03": Path("/data/lerobot_datasets/so101_pick_orange_batch03"),
}

VIDEO_KEYS = [
    "observation.images.front",
    "observation.images.top",
    "observation.images.wrist",
]

DATA_KEYS = [
    "action",
    "observation.state",
    *VIDEO_KEYS,
]

# Start trims measured from the recorded joint trajectories. Each value starts
# just before the first meaningful arm motion, removing the idle beginning that
# taught Pi05 to hold still at episode start.
TRIM_START_SECONDS = {
    "batch01": {
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
    },
    "batch02": {
        0: 2.08,
        1: 2.42,
        2: 3.45,
        3: 2.52,
        4: 1.92,
        5: 2.18,
        6: 2.45,
        7: 2.32,
        8: 3.12,
        9: 2.85,
    },
    "batch03": {
        0: 0.0,
        1: 1.68,
        2: 1.98,
        3: 3.05,
        4: 1.95,
        5: 1.82,
        6: 1.88,
        7: 2.15,
        8: 1.65,
        9: 3.88,
    },
}

# Conservative first-pass end trim map based on visual front/top timeline review.
# Meaning: keep frames through this many seconds, removing the clearest
# rest/extra tail. They are intentionally easy to audit and edit.
TRIM_END_SECONDS = {
    "batch01": {
        0: 24.0,
        1: 27.0,
        2: 24.0,
        3: 24.0,
        4: 24.0,
        5: 24.0,
        6: 24.0,
        7: 24.0,
        8: 24.0,
        9: 24.0,
    },
    "batch02": {
        0: 18.5,
        1: 18.0,
        2: 18.5,
        3: 18.5,
        4: 18.0,
        5: 18.5,
        6: 18.5,
        7: 18.5,
        8: 18.5,
        9: 18.5,
    },
    "batch03": {
        0: 18.5,
        1: 18.0,
        2: 18.0,
        3: 18.5,
        4: 18.5,
        5: 18.5,
        6: 18.5,
        7: 18.5,
        8: 18.5,
        9: 18.5,
    },
}


@dataclass(frozen=True)
class EpisodePlan:
    batch: str
    episode: int
    source_root: Path
    source_length: int
    source_duration_s: float
    keep_start_s: float
    keep_end_s: float
    start_frame: int
    keep_frames: int


def load_episode_plan() -> list[EpisodePlan]:
    plans: list[EpisodePlan] = []
    for batch, root in BATCH_ROOTS.items():
        info = json.loads((root / "meta/info.json").read_text())
        fps = int(info["fps"])
        episodes = pd.read_parquet(root / "meta/episodes/chunk-000/file-000.parquet")
        for _, row in episodes.iterrows():
            ep = int(row["episode_index"])
            source_length = int(row["length"])
            source_duration_s = (source_length - 1) / fps
            keep_start_s = min(max(TRIM_START_SECONDS[batch][ep], 0.0), source_duration_s)
            keep_end_s = min(TRIM_END_SECONDS[batch][ep], source_duration_s)
            if keep_start_s >= keep_end_s:
                raise ValueError(
                    f"Invalid trim for {batch} ep{ep}: start {keep_start_s}s >= end {keep_end_s}s"
                )
            start_frame = int(np.floor(keep_start_s * fps))
            end_frame = int(np.floor(keep_end_s * fps))
            keep_frames = end_frame - start_frame + 1
            keep_frames = max(1, min(keep_frames, source_length))
            plans.append(
                EpisodePlan(
                    batch=batch,
                    episode=ep,
                    source_root=root,
                    source_length=source_length,
                    source_duration_s=source_duration_s,
                    keep_start_s=keep_start_s,
                    keep_end_s=keep_end_s,
                    start_frame=start_frame,
                    keep_frames=keep_frames,
                )
            )
    return plans


def frame_to_uint8_hwc(image) -> np.ndarray:
    """Convert LeRobot reader CHW float tensor image to HWC uint8."""
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


def print_plan(plans: list[EpisodePlan]) -> None:
    print("CLEANED DATASET PLAN")
    print(f"task_text: {TASK_TEXT}")
    print()
    print("batch   ep source_s start_s end_s source_frames keep_frames removed_frames")
    print("-" * 86)
    total_source = 0
    total_keep = 0
    for plan in plans:
        total_source += plan.source_length
        total_keep += plan.keep_frames
        print(
            f"{plan.batch:<7} {plan.episode:>2} "
            f"{plan.source_duration_s:>8.2f} {plan.keep_start_s:>7.2f} {plan.keep_end_s:>5.2f} "
            f"{plan.source_length:>13} {plan.keep_frames:>11} "
            f"{plan.source_length - plan.keep_frames:>14}"
        )
    print("-" * 86)
    print(f"total_source_frames: {total_source}")
    print(f"total_keep_frames:   {total_keep}")
    print(f"removed_frames:      {total_source - total_keep}")
    print(f"removed_seconds:     {(total_source - total_keep) / 30:.2f}")


def build_dataset(output_root: Path, repo_id: str, overwrite: bool) -> None:
    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"{output_root} already exists. Use --overwrite to replace it.")
        shutil.rmtree(output_root)

    plans = load_episode_plan()
    first_source = LeRobotDataset("local/so101_pick_orange_batch01", root=BATCH_ROOTS["batch01"])
    features = make_features(first_source)
    dst = LeRobotDataset.create(
        repo_id=repo_id,
        root=output_root,
        fps=30,
        robot_type="so_follower",
        features=features,
        # Image-only avoids LeRobot's current batch-video metadata edge cases
        # while keeping the same front/top/wrist visual features for training.
        use_videos=False,
        metadata_buffer_size=1,
    )

    source_cache: dict[str, LeRobotDataset] = {"batch01": first_source}
    try:
        for plan in plans:
            if plan.batch not in source_cache:
                source_cache[plan.batch] = LeRobotDataset(
                    f"local/so101_pick_orange_{plan.batch}",
                    root=plan.source_root,
                )
            src = source_cache[plan.batch]
            episodes = pd.read_parquet(plan.source_root / "meta/episodes/chunk-000/file-000.parquet")
            ep_row = episodes[episodes["episode_index"] == plan.episode].iloc[0]
            start_index = int(ep_row["dataset_from_index"]) + plan.start_frame

            print(
                f"writing {plan.batch} ep{plan.episode}: "
                f"start={plan.keep_start_s:.2f}s end={plan.keep_end_s:.2f}s "
                f"{plan.keep_frames}/{plan.source_length} frames"
            )
            for offset in range(plan.keep_frames):
                item = src[start_index + offset]
                frame = {
                    "action": item["action"].numpy(),
                    "observation.state": item["observation.state"].numpy(),
                    "task": TASK_TEXT,
                }
                for key in VIDEO_KEYS:
                    frame[key] = frame_to_uint8_hwc(item[key])
                dst.add_frame(frame)
            dst.save_episode(parallel_encoding=True)
        dst.finalize()
    except Exception:
        # Avoid leaving a partially valid-looking dataset behind after failure.
        if output_root.exists():
            print(f"cleanup_failed: leaving partial output at {output_root} for inspection")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/data/lerobot_datasets/so101_pick_orange_move_action_start_cleaned_images"),
    )
    parser.add_argument("--repo-id", default="local/so101_pick_orange_move_action_start_cleaned_images")
    parser.add_argument("--dry-run", action="store_true", help="Only print the plan.")
    parser.add_argument("--overwrite", action="store_true", help="Replace output-root if it already exists.")
    args = parser.parse_args()

    plans = load_episode_plan()
    print_plan(plans)
    if args.dry_run:
        print()
        print("DRY_RUN_OK: no files written.")
        return

    print()
    print(f"writing cleaned dataset to: {args.output_root}")
    build_dataset(args.output_root, args.repo_id, args.overwrite)
    print()
    print("CLEANED_DATASET_OK")
    print(f"root: {args.output_root}")
    print(f"repo_id: {args.repo_id}")


if __name__ == "__main__":
    main()
