#!/usr/bin/env python3
"""Materialize the audited fine-tune 4 train and validation datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from lerobot.datasets.aggregate import aggregate_datasets
from lerobot.datasets.dataset_tools import delete_episodes, split_dataset
from lerobot.datasets.lerobot_dataset import LeRobotDataset


ORANGE_SOURCE = Path("/home/gaikwad-prakash/orange_grasp_corrective_ft4_20261108")
MATCHBOX_SOURCE = Path("/home/gaikwad-prakash/matchbox_pickplace_ft4_20261108")
OUTPUT_ROOT = Path("/home/gaikwad-prakash/ft4_datasets_20261108")

# The clean orange dataset is reindexed after source episode 0 is removed.
# These correspond to original source episodes [1, 7, 18, 24, 30].
ORANGE_VAL_REINDEXED = [0, 6, 17, 23, 29]
MATCHBOX_VAL = [4]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> list[dict]:
    output = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        output.append(
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return output


def normalize_h264(root: Path) -> None:
    """Give every derived video the same codec before LeRobot concatenates it.

    LeRobot's split helper can emit AV1 for sliced files while retaining the
    source dataset's h264 metadata.  A later merge then interprets AV1 packets
    as h264.  Normalize every split file to one h264 encoding first.
    """
    for path in sorted((root / "videos").glob("**/*.mp4")):
        temporary = path.with_suffix(".normalized.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(path),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                "-movflags",
                "+faststart",
                str(temporary),
            ],
            check=True,
        )
        temporary.replace(path)


def dataset_summary(root: Path, repo_id: str) -> dict:
    dataset = LeRobotDataset(repo_id=repo_id, root=root)
    return {
        "repo_id": repo_id,
        "root": str(root),
        "episodes": dataset.meta.total_episodes,
        "frames": dataset.meta.total_frames,
        "fps": dataset.meta.fps,
        "tasks": sorted(dataset.meta.tasks.index.tolist()),
        "files": inventory(root),
    }


def merge_with_bounded_videos(datasets: list[LeRobotDataset], repo_id: str, root: Path) -> LeRobotDataset:
    """Merge with short video files so random training seeks remain practical."""
    aggregate_datasets(
        repo_ids=[dataset.repo_id for dataset in datasets],
        roots=[dataset.root for dataset in datasets],
        aggr_repo_id=repo_id,
        aggr_root=root,
        video_files_size_in_mb=30,
    )
    return LeRobotDataset(repo_id=repo_id, root=root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--split-output", type=Path, required=True)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text())
    if audit.get("status") != "pass" or audit.get("accepted_episode_count") != 35:
        raise SystemExit("Refusing to prepare datasets: the 35-episode source audit has not passed")

    if OUTPUT_ROOT.exists():
        if not args.rebuild:
            raise SystemExit(f"Output already exists: {OUTPUT_ROOT}; use --rebuild to replace derived data")
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True)

    orange_source = LeRobotDataset(
        repo_id="local/orange_grasp_corrective_ft4_20261108", root=ORANGE_SOURCE
    )
    accepted_root = OUTPUT_ROOT / "orange_accepted30"
    orange_accepted = delete_episodes(
        orange_source,
        episode_indices=[0],
        output_dir=accepted_root,
        repo_id="local/orange_grasp_corrective_ft4_accepted30",
    )
    orange_train = [i for i in range(30) if i not in ORANGE_VAL_REINDEXED]
    orange_splits = split_dataset(
        orange_accepted,
        splits={"train": orange_train, "val": ORANGE_VAL_REINDEXED},
        output_dir=OUTPUT_ROOT / "orange_split",
    )

    matchbox_source = LeRobotDataset(
        repo_id="local/matchbox_pickplace_ft4_20261108", root=MATCHBOX_SOURCE
    )
    matchbox_train = [i for i in range(5) if i not in MATCHBOX_VAL]
    matchbox_splits = split_dataset(
        matchbox_source,
        splits={"train": matchbox_train, "val": MATCHBOX_VAL},
        output_dir=OUTPUT_ROOT / "matchbox_split",
    )

    for split_dataset_object in (*orange_splits.values(), *matchbox_splits.values()):
        normalize_h264(split_dataset_object.root)

    train_root = OUTPUT_ROOT / "train29"
    val_root = OUTPUT_ROOT / "val6"
    train = merge_with_bounded_videos(
        [orange_splits["train"], matchbox_splits["train"]],
        repo_id="local/ft4_orange_matchbox_train29_20261108",
        root=train_root,
    )
    val = merge_with_bounded_videos(
        [orange_splits["val"], matchbox_splits["val"]],
        repo_id="local/ft4_orange_matchbox_val6_20261108",
        root=val_root,
    )

    split = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "policy": "complete episodes; five orange positions represented in validation",
        "source_index_space": True,
        "orange": {
            "source_root": str(ORANGE_SOURCE),
            "rejected": [0],
            "train": [i for i in range(1, 31) if i not in [1, 7, 18, 24, 30]],
            "validation": [1, 7, 18, 24, 30],
            "validation_balance": {
                "direct": [1, 7],
                "lateral_left": [18],
                "lateral_right": [24],
                "depth": [30],
                "positions": ["p0", "p1", "p2", "p3", "p4"],
            },
        },
        "matchbox": {
            "source_root": str(MATCHBOX_SOURCE),
            "train": [0, 1, 2, 3],
            "validation": [4],
        },
        "combined": {"train_episodes": 29, "validation_episodes": 6},
    }
    args.split_output.parent.mkdir(parents=True, exist_ok=True)
    args.split_output.write_text(json.dumps(split, indent=2) + "\n")

    manifest = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "name": "fine_tune_4_orange_acquisition_with_matchbox_auxiliary_20261108",
        "status": "materialized_and_audited",
        "objective": "Improve orange acquisition while retaining a small language-conditioned matchbox selection task.",
        "baseline": {
            "name": "fine-tune 3 row3_all169_conservative_010000",
            "checkpoint_on_ai90": "/home/kiran/lerobot_assets/ckpt_mirror/row3_all169_conservative_010000",
            "controlled_orange_result": "15/57 (26.3%)",
        },
        "source_audit": {
            "path": str(args.audit.resolve()),
            "sha256": sha256(args.audit),
            "accepted_episodes": 35,
            "status": "pass",
        },
        "split": {"path": str(args.split_output.resolve()), "sha256": sha256(args.split_output)},
        "training_mix": {
            "orange_episodes": 25,
            "matchbox_episodes": 4,
            "natural_episode_sampling_weights": {
                "orange": round(25 / 29, 8),
                "matchbox": round(4 / 29, 8),
            },
            "note": "Task strings remain distinct. Matchbox is an auxiliary selection task, not an orange correction label.",
        },
        "validation_mix": {"orange_episodes": 5, "matchbox_episodes": 1},
        "datasets": {
            "train": dataset_summary(train_root, train.repo_id),
            "validation": dataset_summary(val_root, val.repo_id),
        },
        "checkpoint_selection": {
            "save_steps": [1000, 2000, 3000],
            "offline_validation": "Use the six held-out complete episodes only for broken-run screening and candidate ranking.",
            "physical_gates": ["watched 3", "matched 10", "development 50", "blind 100"],
        },
    }
    args.training_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.training_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "status": "pass",
        "output_root": str(OUTPUT_ROOT),
        "train": {"episodes": train.meta.total_episodes, "frames": train.meta.total_frames},
        "validation": {"episodes": val.meta.total_episodes, "frames": val.meta.total_frames},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
