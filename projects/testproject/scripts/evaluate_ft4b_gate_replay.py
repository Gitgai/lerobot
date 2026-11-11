#!/usr/bin/env python3
"""Replay saved FT4B gate observations through checkpoints without robot access."""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch


def load_policy(path: str, horizon: int, inference_steps: int):
    sys.path.insert(0, "/home/kiran/sim/vlash")
    from lerobot.configs.policies import PreTrainedConfig
    import vlash.policies.pi05.configuration_pi05  # noqa: F401
    from vlash.policies.factory import get_policy_class

    cfg = PreTrainedConfig.from_pretrained(path)
    cfg.device = "cuda"
    cfg.empty_cameras = 2
    cfg.n_action_steps = horizon
    cfg.num_inference_steps = inference_steps
    policy = get_policy_class(cfg.type).from_pretrained(path, config=cfg)
    policy.eval()
    image_keys = list(cfg.image_features.keys())
    return policy, image_keys[0], image_keys[1]


def image_tensor(path: Path) -> torch.Tensor:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    rgb = np.ascontiguousarray(bgr[:, :, ::-1])
    return torch.from_numpy(rgb).permute(2, 0, 1).float().div(255).unsqueeze(0).cuda()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ckpts", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=20)
    parser.add_argument("--inference-steps", type=int, default=15)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    rows = []
    predictions: dict[str, dict[str, list[np.ndarray]]] = {}
    for spec in args.ckpts:
        name, checkpoint = spec.split("=", 1)
        policy, front_key, wrist_key = load_policy(checkpoint, args.horizon, args.inference_steps)
        predictions[name] = {}
        for case in manifest["cases"]:
            case_predictions = []
            for repeat in range(args.repeats):
                seed = 111100 + repeat
                torch.manual_seed(seed)
                np.random.seed(seed)
                observation = {
                    front_key: image_tensor(args.manifest.parent / case["front"]),
                    wrist_key: image_tensor(args.manifest.parent / case["wrist"]),
                    "observation.state": torch.tensor(case["state"], dtype=torch.float32, device="cuda").unsqueeze(0),
                    "task": manifest["task"],
                }
                with torch.inference_mode():
                    prediction = policy.predict_action_chunk(observation)[0, : args.horizon].float().cpu().numpy()
                case_predictions.append(prediction)
                historical = np.asarray(case["historical_actions"], dtype=np.float32)[: args.horizon]
                rows.append({
                    "checkpoint": name, "case": case["name"], "trial": case["trial"],
                    "chunk": case["chunk"], "repeat": repeat + 1,
                    "historical_mae": round(float(np.mean(np.abs(prediction - historical))), 5),
                    "predicted_gripper_min": round(float(prediction[:, 5].min()), 4),
                    "predicted_gripper_last": round(float(prediction[-1, 5]), 4),
                    "first_action": prediction[0].round(4).tolist(),
                    "last_action": prediction[-1].round(4).tolist(),
                })
            predictions[name][case["name"]] = case_predictions
        del policy
        gc.collect()
        torch.cuda.empty_cache()

    checkpoint_names = list(predictions)
    comparisons = []
    if len(checkpoint_names) == 2:
        left, right = checkpoint_names
        for case in manifest["cases"]:
            left_values = np.stack(predictions[left][case["name"]])
            right_values = np.stack(predictions[right][case["name"]])
            comparisons.append({
                "case": case["name"], "trial": case["trial"], "chunk": case["chunk"],
                "checkpoint_mae_same_seeds": round(float(np.mean(np.abs(left_values - right_values))), 5),
                "arm_mae_same_seeds": round(float(np.mean(np.abs(left_values[:, :, :5] - right_values[:, :, :5]))), 5),
                "gripper_mae_same_seeds": round(float(np.mean(np.abs(left_values[:, :, 5] - right_values[:, :, 5]))), 5),
            })
    report = {
        "scope": "Saved images and measured joint states only; no cameras or robot opened.",
        "task": manifest["task"], "horizon": args.horizon,
        "inference_steps": args.inference_steps, "repeats": args.repeats,
        "rows": rows, "checkpoint_comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    summary = {}
    for name in checkpoint_names:
        selected = [row for row in rows if row["checkpoint"] == name]
        summary[name] = {
            "historical_mae_mean": round(float(np.mean([row["historical_mae"] for row in selected])), 5),
            "predicted_gripper_min_mean": round(float(np.mean([row["predicted_gripper_min"] for row in selected])), 4),
        }
    print(json.dumps({"summary": summary, "checkpoint_comparisons": comparisons}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
