#!/usr/bin/env python3
"""Compare a Pi05 checkpoint against recorded actions from one episode.

This script never opens robot serial ports and never moves the real arm. It
loads a LeRobot dataset episode, asks Pi05 for an action chunk at selected
frames, post-processes the predicted chunk back into real joint units, and
compares it to the recorded future actions.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import torch

from lerobot.configs import PreTrainedConfig
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.factory import get_policy_class, make_pre_post_processors


MOTORS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]


def parse_indices(raw: str | None, length: int, chunk_size: int) -> list[int]:
    if raw:
        indices = [int(part.strip()) for part in raw.split(",") if part.strip()]
    else:
        # Cover start, approach, grasp/lift, and late move/drop regions.
        fractions = [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
        max_start = max(0, length - chunk_size - 1)
        indices = [round(frac * max_start) for frac in fractions]
    return sorted(set(max(0, min(index, length - chunk_size - 1)) for index in indices))


def tensor_to_list(value: torch.Tensor) -> list[float]:
    return [float(x) for x in value.detach().cpu().flatten().tolist()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--dataset-repo-id", default="local/so101_pick_orange_episode29_overfit")
    parser.add_argument("--policy-path", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--indices", default=None, help="Comma-separated frame indices. Default samples the episode.")
    parser.add_argument("--chunk-size", type=int, default=50)
    parser.add_argument("--max-compare-actions", type=int, default=50)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--video-backend", default="pyav")
    args = parser.parse_args()

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    print("PI05 EPISODE OFFLINE ACTION COMPARISON")
    print(f"dataset_root: {args.dataset_root}")
    print(f"policy_path:  {args.policy_path}")
    print(f"output_csv:   {output_csv}")

    dataset = LeRobotDataset(args.dataset_repo_id, root=args.dataset_root, video_backend=args.video_backend)
    indices = parse_indices(args.indices, len(dataset), args.chunk_size)
    print(f"dataset_frames: {len(dataset)}")
    print(f"sample_indices: {indices}")

    cfg = PreTrainedConfig.from_pretrained(args.policy_path)
    cfg.device = args.device
    policy_cls = get_policy_class(cfg.type)
    policy = policy_cls.from_pretrained(args.policy_path, config=cfg)
    policy.eval()

    preprocessor, postprocessor = make_pre_post_processors(cfg, pretrained_path=args.policy_path)

    rows: list[dict[str, float | int | str]] = []
    summary_rows: list[dict[str, float | int | str]] = []

    with torch.no_grad():
        for frame_index in indices:
            item = dict(dataset[frame_index])
            processed = preprocessor(item)
            pred_norm = policy.predict_action_chunk(processed)
            pred = postprocessor(pred_norm)
            pred = pred.squeeze(0).detach().cpu()

            compare_n = min(args.max_compare_actions, pred.shape[0], len(dataset) - frame_index)
            recorded = torch.stack([dataset[frame_index + offset]["action"] for offset in range(compare_n)])
            pred = pred[:compare_n]
            abs_error = (pred - recorded).abs()

            timestamp = float(item["timestamp"])
            first_pred = tensor_to_list(pred[0])
            first_recorded = tensor_to_list(recorded[0])
            first_error = tensor_to_list(abs_error[0])
            print()
            print(f"frame {frame_index}  t={timestamp:.3f}s  compare_actions={compare_n}")
            print(f"  recorded[0]: {[round(x, 3) for x in first_recorded]}")
            print(f"  predicted[0]: {[round(x, 3) for x in first_pred]}")
            print(f"  abs_error[0]: {[round(x, 3) for x in first_error]}")

            for motor_index, motor in enumerate(MOTORS):
                motor_errors = abs_error[:, motor_index]
                summary_rows.append(
                    {
                        "frame_index": frame_index,
                        "timestamp_s": timestamp,
                        "motor": motor,
                        "mean_abs_error": float(motor_errors.mean().item()),
                        "max_abs_error": float(motor_errors.max().item()),
                        "first_recorded": float(recorded[0, motor_index].item()),
                        "first_predicted": float(pred[0, motor_index].item()),
                        "first_abs_error": float(abs_error[0, motor_index].item()),
                    }
                )

            for offset in range(compare_n):
                row: dict[str, float | int | str] = {
                    "frame_index": frame_index,
                    "timestamp_s": timestamp,
                    "chunk_offset": offset,
                    "future_frame_index": frame_index + offset,
                    "future_timestamp_s": float(dataset[frame_index + offset]["timestamp"]),
                }
                for motor_index, motor in enumerate(MOTORS):
                    row[f"{motor}.recorded"] = float(recorded[offset, motor_index].item())
                    row[f"{motor}.predicted"] = float(pred[offset, motor_index].item())
                    row[f"{motor}.abs_error"] = float(abs_error[offset, motor_index].item())
                rows.append(row)

    with output_csv.open("w", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_csv = output_csv.with_suffix(".summary.csv")
    with summary_csv.open("w", newline="") as f:
        fieldnames = list(summary_rows[0].keys()) if summary_rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print()
    print("SUMMARY mean absolute error over compared chunks:")
    by_motor: dict[str, list[float]] = {motor: [] for motor in MOTORS}
    by_motor_max: dict[str, list[float]] = {motor: [] for motor in MOTORS}
    for row in summary_rows:
        by_motor[str(row["motor"])].append(float(row["mean_abs_error"]))
        by_motor_max[str(row["motor"])].append(float(row["max_abs_error"]))
    for motor in MOTORS:
        mean_error = sum(by_motor[motor]) / max(1, len(by_motor[motor]))
        max_error = max(by_motor_max[motor]) if by_motor_max[motor] else math.nan
        print(f"  {motor:14s} mean_abs_error={mean_error:8.3f}  max_abs_error={max_error:8.3f}")

    print()
    print("OFFLINE_COMPARE_OK")
    print(f"csv: {output_csv}")
    print(f"summary_csv: {summary_csv}")


if __name__ == "__main__":
    main()
