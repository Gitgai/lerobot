#!/usr/bin/env python3
"""Verify the FT4 trimmed/phase-weighted derivative against its sources."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from lerobot.datasets.lerobot_dataset import LeRobotDataset


ROOT = Path("/home/gaikwad-prakash/ft4_reweighted_20261110")
OUTPUT = Path(
    "projects/testproject/results/so101_bench_20261019/"
    "ft4_reweighted_dataset_20261110/audit.json"
)
SOURCES = {
    "orange": Path("/home/gaikwad-prakash/orange_grasp_corrective_ft4_20261108"),
    "matchbox": Path("/home/gaikwad-prakash/matchbox_pickplace_ft4_20261108"),
}
EXPECTED = {"train54": (54, 42024), "val6": (6, 5907)}


def dataset(name: str, root: Path) -> LeRobotDataset:
    return LeRobotDataset(
        repo_id=f"local/audit-{name}", root=root, video_backend="pyav", return_uint8=True
    )


def main() -> int:
    errors: list[str] = []
    source_ds = {kind: dataset(f"source-{kind}", root) for kind, root in SOURCES.items()}
    columns = ["index", "episode_index", "frame_index", "action", "observation.state"]
    source_data = {
        kind: value.select_columns(columns).to_pandas() for kind, value in source_ds.items()
    }
    report: dict = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "subsets": {},
    }
    split_sources: dict[str, set[tuple[str, int]]] = {}

    for subset, (expected_episodes, expected_frames) in EXPECTED.items():
        root = ROOT / subset
        derived = dataset(subset, root)
        data = derived.select_columns(columns + ["task_index"]).to_pandas()
        mapping = pd.read_csv(root / "meta/source_mapping.csv")
        subset_errors: list[str] = []
        if derived.meta.total_episodes != expected_episodes:
            subset_errors.append(
                f"episodes={derived.meta.total_episodes}, expected={expected_episodes}"
            )
        if derived.meta.total_frames != expected_frames:
            subset_errors.append(f"frames={derived.meta.total_frames}, expected={expected_frames}")
        if not np.array_equal(data["index"].to_numpy(), np.arange(len(data))):
            subset_errors.append("global indices are not contiguous")

        camera_pairs = 0
        motion_onsets: list[int] = []
        for row in mapping.itertuples(index=False):
            output = data[data.episode_index == row.output_episode].reset_index(drop=True)
            source = source_data[row.source_kind]
            source = source[source.episode_index == row.source_episode].sort_values("frame_index")
            source = source.iloc[row.source_start_frame : row.source_stop_exclusive].reset_index(drop=True)
            if len(output) != row.frames or len(source) != row.frames:
                subset_errors.append(f"episode {row.output_episode}: length mismatch")
                continue
            if not np.array_equal(output.frame_index.to_numpy(), np.arange(len(output))):
                subset_errors.append(f"episode {row.output_episode}: frame indices not contiguous")
            if not np.array_equal(np.stack(output.action), np.stack(source.action)):
                subset_errors.append(f"episode {row.output_episode}: actions differ from source")
            if not np.array_equal(
                np.stack(output["observation.state"]), np.stack(source["observation.state"])
            ):
                subset_errors.append(f"episode {row.output_episode}: states differ from source")

            actions = np.stack(output.action)
            motion = np.flatnonzero(np.max(np.abs(actions[:, :5] - actions[0, :5]), axis=1) >= 3)
            if not len(motion):
                subset_errors.append(f"episode {row.output_episode}: no >=3 degree motion")
            else:
                motion_onsets.append(int(motion[0]))

            for local_index in sorted({0, len(output) // 2, len(output) - 1}):
                output_index = int(output.iloc[local_index]["index"])
                source_index = int(source.iloc[local_index]["index"])
                output_item = derived[output_index]
                source_item = source_ds[row.source_kind][source_index]
                for camera in ("observation.images.front", "observation.images.wrist"):
                    if not np.array_equal(
                        output_item[camera].numpy(), source_item[camera].numpy()
                    ):
                        subset_errors.append(
                            f"episode {row.output_episode} frame {local_index}: {camera} differs"
                        )
                camera_pairs += 1

        tasks = derived.meta.tasks.index.tolist()
        expected_tasks = [
            "pick up the orange and place it on the plate",
            "pick up the matchbox and place it on the plate",
        ]
        if tasks != expected_tasks:
            subset_errors.append(f"task table differs: {tasks}")
        split_sources[subset] = {
            (str(row.source_kind), int(row.source_episode)) for row in mapping.itertuples(index=False)
        }
        errors.extend(f"{subset}: {message}" for message in subset_errors)
        report["subsets"][subset] = {
            "episodes": derived.meta.total_episodes,
            "frames": derived.meta.total_frames,
            "tasks": tasks,
            "paired_camera_samples": camera_pairs,
            "motion_onset_frames": {
                "min": min(motion_onsets),
                "median": float(np.median(motion_onsets)),
                "max": max(motion_onsets),
                "within_first_10": sum(value <= 10 for value in motion_onsets),
                "total": len(motion_onsets),
            },
            "composition": mapping.groupby(["kind", "source_kind"])["frames"]
            .agg(["count", "sum"])
            .reset_index()
            .to_dict(orient="records"),
            "errors": subset_errors,
        }

    overlap = split_sources["train54"] & split_sources["val6"]
    if overlap:
        errors.append(f"source episode leakage between train and validation: {sorted(overlap)}")
    report["source_episode_overlap"] = sorted(overlap)
    report["errors"] = errors
    report["status"] = "pass" if not errors else "fail"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
