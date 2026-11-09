#!/usr/bin/env python3
"""Audit FT4 demonstration openings and training exposure without decoding videos."""

import collections
import glob
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


ORANGE = Path("/home/gaikwad-prakash/orange_grasp_corrective_ft4_20261108")
MATCHBOX = Path("/home/gaikwad-prakash/matchbox_pickplace_ft4_20261108")
DEPLOYED_START = np.array([-5.0, -104.0, 97.0, 78.0, -2.0, 65.0])
ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "ft4_dataset_20261108" / "episode_split.json"
RUN = ROOT / "ft4_dataset_20261108" / "training_run_summary.json"


def read_episodes(root, accepted):
    episodes = collections.defaultdict(list)
    for name in glob.glob(str(root / "data" / "**" / "*.parquet"), recursive=True):
        table = pq.read_table(name, columns=["episode_index", "frame_index", "timestamp", "action"])
        for row in table.to_pylist():
            if row["episode_index"] in accepted:
                episodes[row["episode_index"]].append(row)
    return episodes


def category(kind, episode):
    if kind == "matchbox":
        return "matchbox"
    if episode <= 15:
        return "orange_direct"
    if episode <= 20:
        return "orange_lateral_left"
    if episode <= 25:
        return "orange_lateral_right"
    return "orange_depth"


def summarize(values):
    values = np.asarray(values, dtype=float)
    return {
        "min": float(values.min()),
        "median": float(np.median(values)),
        "max": float(values.max()),
    }


def main():
    split = json.loads(SPLIT.read_text())
    train = {
        "orange": set(split["orange"]["train"]),
        "matchbox": set(split["matchbox"]["train"]),
    }
    validation = {
        "orange": set(split["orange"]["validation"]),
        "matchbox": set(split["matchbox"]["validation"]),
    }
    sources = {
        "orange": (ORANGE, set(range(1, 31))),
        "matchbox": (MATCHBOX, set(range(5))),
    }
    rows = []
    for kind, (root, accepted) in sources.items():
        for episode, episode_rows in sorted(read_episodes(root, accepted).items()):
            episode_rows.sort(key=lambda row: row["frame_index"])
            actions = np.asarray([row["action"] for row in episode_rows], dtype=float)
            times = np.asarray([row["timestamp"] for row in episode_rows], dtype=float)
            start = np.median(actions[:10], axis=0)
            motion_score = np.max(np.abs(actions[:, :5] - start[:5]), axis=1)
            reach_score = np.maximum(actions[:, 1] - start[1], start[2] - actions[:, 2])
            motion_index = np.flatnonzero(motion_score >= 3.0)
            reach_index = np.flatnonzero(reach_score >= 15.0)
            delta = np.max(np.abs(np.diff(actions, axis=0)), axis=1)
            active_index = np.flatnonzero(delta >= 0.2) + 1
            subset = "train" if episode in train[kind] else "validation"
            rows.append({
                "object": kind,
                "episode": episode,
                "category": category(kind, episode),
                "subset": subset,
                "frames": len(episode_rows),
                "duration_s": float(times[-1]),
                "motion_onset_s": float(times[motion_index[0]]),
                "reach_onset_s": float(times[reach_index[0]]),
                "pre_reach_frames": int(reach_index[0]),
                "last_active_s": float(times[active_index[-1]]),
                "end_idle_s": float(times[-1] - times[active_index[-1]]),
                "start_pose": start.round(4).tolist(),
                "start_arm_mae_from_deployed_deg": float(np.mean(np.abs(start[:5] - DEPLOYED_START[:5]))),
                "start_arm_max_error_from_deployed_deg": float(np.max(np.abs(start[:5] - DEPLOYED_START[:5]))),
                "start_gripper_deg": float(start[5]),
            })

    orange = [row for row in rows if row["object"] == "orange"]
    matchbox = [row for row in rows if row["object"] == "matchbox"]
    train_rows = [row for row in rows if row["subset"] == "train"]
    run = json.loads(RUN.read_text())
    report = {
        "scope": "All 35 visually accepted FT4 source episodes; rejected orange episode 0 excluded.",
        "definitions": {
            "motion_onset": "First frame with >=3 degree change in any of the five arm joints from the median first ten actions.",
            "reach_onset": "First frame with >=15 degree shoulder-lift unfolding or elbow unfolding from the median first ten actions.",
            "start_pose_reference": DEPLOYED_START.tolist(),
        },
        "summary": {
            "orange_episodes": len(orange),
            "matchbox_episodes": len(matchbox),
            "orange_motion_onset_s": summarize([row["motion_onset_s"] for row in orange]),
            "orange_reach_onset_s": summarize([row["reach_onset_s"] for row in orange]),
            "orange_reach_within_2s": sum(row["reach_onset_s"] <= 2 for row in orange),
            "orange_start_arm_mae_deg": summarize([row["start_arm_mae_from_deployed_deg"] for row in orange]),
            "orange_start_arm_max_error_deg": summarize([row["start_arm_max_error_from_deployed_deg"] for row in orange]),
            "orange_start_within_2deg_all_arm_joints": sum(row["start_arm_max_error_from_deployed_deg"] <= 2 for row in orange),
            "orange_start_gripper_deg": summarize([row["start_gripper_deg"] for row in orange]),
            "orange_start_gripper_at_least_60deg": sum(row["start_gripper_deg"] >= 60 for row in orange),
            "orange_start_gripper_at_least_64deg": sum(row["start_gripper_deg"] >= 64 for row in orange),
            "matchbox_reach_onset_s": summarize([row["reach_onset_s"] for row in matchbox]),
            "training_pre_reach_frames": sum(row["pre_reach_frames"] for row in train_rows),
            "training_total_frames_from_sources": sum(row["frames"] for row in train_rows),
            "training_pre_reach_fraction": sum(row["pre_reach_frames"] for row in train_rows) / sum(row["frames"] for row in train_rows),
            "training_samples_processed": run["samples"],
            "training_dataset_frames": 30376,
            "effective_epochs": run["effective_epochs"],
            "new_training_task": "pick up the orange and place it on the plate",
            "deployed_trial_task": "Grab oranges and place into plate.",
            "task_strings_exact_match": False,
            "explicit_sampling_weights": False,
            "natural_episode_mix": {"orange": "25/29", "matchbox": "4/29"},
        },
        "episodes": rows,
    }
    output = Path(__file__).with_name("audit.json")
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
