#!/usr/bin/env python3
"""Replay a Pi05 action log in software and compare raw vs sent targets.

This is not a physics simulator. It is a joint-space replay that answers:
"Would removing LeRobot's per-step guard have changed the commanded motion?"
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


MOTORS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

DEFAULT_LOG = Path(
    "/data/downloads/3cam tests/"
    "pi05_episode29_overfit_003000_realarm_50actions_20260703_231147.actions.csv"
)
DEFAULT_OUT_DIR = Path("/data/downloads/3cam tests")


def load_action_log(path: Path) -> tuple[dict[str, float], dict[str, float], list[dict[str, float]], list[dict[str, float]]]:
    before: dict[str, float] | None = None
    after: dict[str, float] | None = None
    commanded: list[dict[str, float]] = []
    sent: list[dict[str, float]] = []

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pose = {motor: float(row[f"{motor}.pos"]) for motor in MOTORS}
            phase = row["phase"]
            if phase == "before":
                before = pose
            elif phase == "after":
                after = pose
            elif phase == "commanded":
                commanded.append(pose)
            elif phase == "sent":
                sent.append(pose)

    if before is None:
        raise ValueError(f"{path} does not contain a 'before' row")
    if after is None:
        raise ValueError(f"{path} does not contain an 'after' row")
    if len(commanded) != len(sent):
        raise ValueError(f"commanded rows ({len(commanded)}) and sent rows ({len(sent)}) do not match")
    if not commanded:
        raise ValueError(f"{path} does not contain commanded/sent actions")

    return before, after, commanded, sent


def pose_array(poses: list[dict[str, float]]) -> np.ndarray:
    return np.array([[pose[motor] for motor in MOTORS] for pose in poses], dtype=float)


def write_summary(
    path: Path,
    before: dict[str, float],
    after: dict[str, float],
    commanded: np.ndarray,
    sent: np.ndarray,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    first_commanded = commanded[0]
    first_sent = sent[0]
    last_commanded = commanded[-1]
    last_sent = sent[-1]
    delta = commanded - sent

    for idx, motor in enumerate(MOTORS):
        rows.append(
            {
                "motor": motor,
                "before": before[motor],
                "after_real": after[motor],
                "raw_first_target": first_commanded[idx],
                "sent_first_target": first_sent[idx],
                "raw_first_delta_from_before": first_commanded[idx] - before[motor],
                "sent_first_delta_from_before": first_sent[idx] - before[motor],
                "raw_last_target": last_commanded[idx],
                "sent_last_target": last_sent[idx],
                "raw_min_target": float(commanded[:, idx].min()),
                "raw_max_target": float(commanded[:, idx].max()),
                "sent_min_target": float(sent[:, idx].min()),
                "sent_max_target": float(sent[:, idx].max()),
                "mean_abs_raw_minus_sent": float(np.abs(delta[:, idx]).mean()),
                "max_abs_raw_minus_sent": float(np.abs(delta[:, idx]).max()),
            }
        )

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows


def plot_trajectories(path: Path, before: dict[str, float], after: dict[str, float], commanded: np.ndarray, sent: np.ndarray) -> None:
    steps = np.arange(len(commanded))
    fig, axes = plt.subplots(3, 2, figsize=(14, 10), sharex=True)
    axes = axes.ravel()

    for idx, motor in enumerate(MOTORS):
        ax = axes[idx]
        ax.plot(steps, commanded[:, idx], label="raw Pi05 commanded", color="#d55e00", linewidth=2)
        ax.plot(steps, sent[:, idx], label="LeRobot sent", color="#0072b2", linestyle="--", linewidth=2)
        ax.axhline(before[motor], color="#666666", linestyle=":", linewidth=1.5, label="before" if idx == 0 else None)
        ax.axhline(after[motor], color="#009e73", linestyle="-.", linewidth=1.5, label="real after" if idx == 0 else None)
        ax.set_title(motor)
        ax.set_ylabel("deg / gripper units")
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("action index")
    axes[-2].set_xlabel("action index")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4)
    fig.suptitle("Pi05 raw action replay: commanded targets vs LeRobot-sent targets", y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def draw_arm_schematic(ax: plt.Axes, pose: np.ndarray, title: str) -> None:
    shoulder_lift = math.radians(pose[MOTORS.index("shoulder_lift")] + 95.0)
    elbow_flex = math.radians(pose[MOTORS.index("elbow_flex")] - 90.0)
    wrist_flex = math.radians(pose[MOTORS.index("wrist_flex")] - 80.0)
    shoulder_pan = math.radians(pose[MOTORS.index("shoulder_pan")])
    wrist_roll = pose[MOTORS.index("wrist_roll")]
    gripper = pose[MOTORS.index("gripper")]

    lengths = [1.0, 0.85, 0.45]
    angles = [
        shoulder_lift,
        shoulder_lift - elbow_flex,
        shoulder_lift - elbow_flex + wrist_flex,
    ]

    points = [(0.0, 0.0)]
    x, y = 0.0, 0.0
    for length, angle in zip(lengths, angles):
        x += length * math.cos(angle)
        y += length * math.sin(angle)
        points.append((x, y))

    xs, ys = zip(*points)
    ax.plot(xs, ys, "-o", color="#0072b2", linewidth=5, markersize=7)

    grip_open = np.clip((gripper - 15.0) / 45.0, 0.0, 1.0)
    finger_len = 0.22
    spread = 0.07 + 0.15 * grip_open
    wrist_angle = angles[-1]
    tip_x, tip_y = points[-1]
    normal = wrist_angle + math.pi / 2
    for sign in [-1, 1]:
        base_x = tip_x + sign * spread * math.cos(normal)
        base_y = tip_y + sign * spread * math.sin(normal)
        end_x = base_x + finger_len * math.cos(wrist_angle)
        end_y = base_y + finger_len * math.sin(wrist_angle)
        ax.plot([base_x, end_x], [base_y, end_y], color="#d55e00", linewidth=4)

    pan_x = 0.55 * math.sin(shoulder_pan)
    pan_y = -1.1
    ax.plot([0, pan_x], [pan_y, pan_y + 0.35], color="#009e73", linewidth=4)
    ax.text(-1.65, -1.25, f"pan {math.degrees(shoulder_pan):.1f}\nwrist_roll {wrist_roll:.1f}\ngripper {gripper:.1f}", fontsize=9)

    ax.set_title(title)
    ax.set_xlim(-1.8, 2.4)
    ax.set_ylim(-1.4, 1.8)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2)
    ax.set_xticks([])
    ax.set_yticks([])


def make_replay_video(path: Path, before: dict[str, float], commanded: np.ndarray, sent: np.ndarray, fps: float) -> None:
    frames: list[np.ndarray] = []
    before_arr = np.array([before[motor] for motor in MOTORS], dtype=float)

    for step in range(len(commanded)):
        fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=120)
        draw_arm_schematic(axes[0], commanded[step], f"Raw Pi05 target {step + 1}/{len(commanded)}")
        draw_arm_schematic(axes[1], sent[step], f"LeRobot-sent target {step + 1}/{len(sent)}")

        raw_delta = commanded[step] - before_arr
        sent_delta = sent[step] - before_arr
        max_extra = float(np.abs(commanded[step] - sent[step]).max())
        fig.suptitle(
            f"Joint-space replay only | max raw-vs-sent difference this step: {max_extra:.2f}",
            fontsize=12,
        )
        fig.text(
            0.5,
            0.02,
            "raw first/continuing deltas from start: "
            + ", ".join(f"{m} {raw_delta[i]:+.1f}" for i, m in enumerate(MOTORS[:3]))
            + " | "
            + ", ".join(f"{m} {raw_delta[i]:+.1f}" for i, m in enumerate(MOTORS[3:], start=3)),
            ha="center",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.05, 1, 0.92))
        fig.canvas.draw()
        rgba = np.asarray(fig.canvas.buffer_rgba())
        frame = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        frames.append(frame)
        plt.close(fig)

    height, width = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for frame in frames:
        writer.write(frame)
    writer.release()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actions-csv", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--fps", type=float, default=5.0)
    args = parser.parse_args()

    before, after, commanded_rows, sent_rows = load_action_log(args.actions_csv)
    commanded = pose_array(commanded_rows)
    sent = pose_array(sent_rows)

    prefix = args.prefix or args.actions_csv.stem.replace(".actions", "") + "_raw_action_replay"
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = args.out_dir / f"{prefix}.summary.csv"
    plot_path = args.out_dir / f"{prefix}.png"
    video_path = args.out_dir / f"{prefix}.mp4"

    rows = write_summary(summary_path, before, after, commanded, sent)
    plot_trajectories(plot_path, before, after, commanded, sent)
    make_replay_video(video_path, before, commanded, sent, args.fps)

    print("RAW_ACTION_REPLAY_OK")
    print(f"actions: {len(commanded)}")
    print(f"summary: {summary_path}")
    print(f"plot:    {plot_path}")
    print(f"video:   {video_path}")
    print()
    print("Largest raw-vs-sent differences:")
    for row in sorted(rows, key=lambda r: float(r["max_abs_raw_minus_sent"]), reverse=True):
        print(
            f"{row['motor']:14s} "
            f"mean={float(row['mean_abs_raw_minus_sent']):7.3f} "
            f"max={float(row['max_abs_raw_minus_sent']):7.3f} "
            f"raw_first_delta={float(row['raw_first_delta_from_before']):+8.3f} "
            f"sent_first_delta={float(row['sent_first_delta_from_before']):+8.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
