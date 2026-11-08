#!/usr/bin/env python3
"""Compare fine-tune 4 checkpoints on complete held-out LeRobot v3 episodes.

This is an offline ranking signal only.  It compares each checkpoint's next
ten predicted actions with the recorded expert actions at fixed probe frames.
Physical robot trials remain the success criterion.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import av
import numpy as np
import pandas as pd
import torch


JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def load_data(root: Path) -> pd.DataFrame:
    frames = [pd.read_parquet(path) for path in sorted((root / "data").glob("**/*.parquet"))]
    data = pd.concat(frames, ignore_index=True).sort_values("index").reset_index(drop=True)
    if not np.array_equal(data["index"].to_numpy(), np.arange(len(data))):
        raise RuntimeError("Dataset global frame indices are not contiguous")
    return data


def decode_selected(path: Path, selected: set[int]) -> dict[int, np.ndarray]:
    output: dict[int, np.ndarray] = {}
    with av.open(str(path)) as container:
        for index, frame in enumerate(container.decode(video=0)):
            if index in selected:
                output[index] = frame.to_ndarray(format="rgb24")
    missing = selected - output.keys()
    if missing:
        raise RuntimeError(f"Video {path} is missing selected frames: {sorted(missing)[:10]}")
    return output


def load_policy(path: str):
    sys.path.insert(0, "/home/kiran/sim/vlash")
    from lerobot.configs.policies import PreTrainedConfig
    import vlash.policies.pi05.configuration_pi05  # noqa: F401
    from vlash.policies.factory import get_policy_class

    cfg = PreTrainedConfig.from_pretrained(path)
    cfg.device = "cuda"
    cfg.n_action_steps = 10
    cfg.num_inference_steps = 10
    policy = get_policy_class(cfg.type).from_pretrained(path, config=cfg)
    policy.eval()
    image_keys = list(cfg.image_features.keys())
    front_key = next(key for key in image_keys if "front" in key)
    wrist_key = next(key for key in image_keys if "wrist" in key)
    return policy, front_key, wrist_key


def summarize(errors: np.ndarray, grip_agreement: list[bool]) -> dict:
    return {
        "mae_per_joint": dict(zip(JOINTS, errors.mean(axis=0).round(4).tolist(), strict=True)),
        "mae_arm_joints_mean": round(float(errors[:, :5].mean()), 4),
        "mae_gripper": round(float(errors[:, 5].mean()), 4),
        "mae_all": round(float(errors.mean()), 4),
        "gripper_open_close_agreement_at_step10": round(float(np.mean(grip_agreement)), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--ckpts", nargs="+", required=True, help="name=/path/to/pretrained_model")
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--horizon", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data = load_data(args.dataset)
    tasks_table = pd.read_parquet(args.dataset / "meta/tasks.parquet")
    task_by_index = {int(row.task_index): str(task) for task, row in tasks_table.iterrows()}
    actions = np.stack(data["action"].to_numpy()).astype(np.float32)
    states = np.stack(data["observation.state"].to_numpy()).astype(np.float32)

    probes = []
    for episode, episode_data in data.groupby("episode_index", sort=True):
        indices = episode_data.index.to_numpy()
        start, stop = int(indices[0]), int(indices[-1]) + 1
        task = task_by_index[int(episode_data["task_index"].iloc[0])]
        for index in range(start, stop - args.horizon - 1, args.stride):
            probes.append((int(episode), index, task))

    selected = {index for _, index, _ in probes}
    front_path = next((args.dataset / "videos/observation.images.front").glob("**/*.mp4"))
    wrist_path = next((args.dataset / "videos/observation.images.wrist").glob("**/*.mp4"))
    front = decode_selected(front_path, selected)
    wrist = decode_selected(wrist_path, selected)
    print(f"Loaded {len(probes)} probes from {data.episode_index.nunique()} held-out episodes", flush=True)

    results = {}
    for checkpoint_spec in args.ckpts:
        name, checkpoint = checkpoint_spec.split("=", 1)
        policy, front_key, wrist_key = load_policy(checkpoint)
        all_errors, all_grip, tasks = [], [], []
        started = time.time()
        torch.manual_seed(1108)
        np.random.seed(1108)
        for episode, index, task in probes:
            observation = {
                front_key: torch.from_numpy(front[index]).permute(2, 0, 1).float().div(255).unsqueeze(0).cuda(),
                wrist_key: torch.from_numpy(wrist[index]).permute(2, 0, 1).float().div(255).unsqueeze(0).cuda(),
                "observation.state": torch.from_numpy(states[index]).unsqueeze(0).cuda(),
                "task": task,
            }
            with torch.inference_mode():
                predicted = policy.predict_action_chunk(observation)[0, : args.horizon].float().cpu().numpy()
            target = actions[index + 1 : index + 1 + args.horizon]
            all_errors.append(np.abs(predicted - target).mean(axis=0))
            all_grip.append(bool((predicted[-1, 5] > 25) == (target[-1, 5] > 25)))
            tasks.append(task)

        errors = np.stack(all_errors)
        result = {
            "checkpoint": checkpoint,
            "probes": len(probes),
            **summarize(errors, all_grip),
            "by_task": {},
            "seconds": round(time.time() - started, 2),
        }
        for task in sorted(set(tasks)):
            mask = np.array([value == task for value in tasks])
            task_grip = [value for value, keep in zip(all_grip, mask, strict=True) if keep]
            result["by_task"][task] = {"probes": int(mask.sum()), **summarize(errors[mask], task_grip)}
        results[name] = result
        print(name, json.dumps(result), flush=True)
        del policy
        gc.collect()
        torch.cuda.empty_cache()

    ranking = sorted(results, key=lambda name: (results[name]["mae_all"], -results[name]["gripper_open_close_agreement_at_step10"]))
    report = {
        "dataset": str(args.dataset),
        "episodes": sorted(int(value) for value in data.episode_index.unique()),
        "stride": args.stride,
        "horizon": args.horizon,
        "ranking_by_mae": ranking,
        "results": results,
        "caution": "Offline action imitation is a candidate-screening metric; robot success must be measured physically.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
