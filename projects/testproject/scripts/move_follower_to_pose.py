#!/usr/bin/env python3
"""Move the SO-101 follower toward a target pose in safe incremental steps."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "so101.json"

MOTOR_ORDER = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

DEFAULT_TARGET = {
    "shoulder_pan": -3.0,
    "shoulder_lift": 13.0,
    "elbow_flex": 31.0,
    "wrist_flex": 93.0,
    "wrist_roll": 101.0,
    "gripper": 24.0,
}


def load_project_config() -> dict:
    with CONFIG_PATH.open() as f:
        return json.load(f)


def resolve_follower_port(cfg: dict) -> str:
    serial_path = Path(cfg["follower_serial"])
    if serial_path.exists():
        try:
            return str(serial_path.resolve())
        except OSError:
            return str(serial_path)
    return str(cfg["follower_port"])


def nearest_equivalent(target: float, current: float) -> float:
    candidates = [target - 360.0, target, target + 360.0]
    return min(candidates, key=lambda value: abs(value - current))


def format_pose(pose: dict[str, float]) -> str:
    lines = []
    for motor in MOTOR_ORDER:
        lines.append(f"{motor:16s} {pose[motor]:8.2f}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=30, help="Maximum number of control iterations.")
    parser.add_argument("--settle-s", type=float, default=0.35, help="Pause between iterations.")
    parser.add_argument(
        "--max-relative-target",
        type=float,
        default=5.0,
        help="Maximum per-joint change allowed by LeRobot at each iteration.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=6.0,
        help="Stop once every joint is within this many degrees/percent of target.",
    )
    parser.add_argument(
        "--skip-wrist-roll",
        action="store_true",
        help="Leave wrist_roll at its current value if you do not want software to rotate it.",
    )
    args = parser.parse_args()

    cfg = load_project_config()
    port = resolve_follower_port(cfg)

    robot_cfg = SOFollowerRobotConfig(
        port=port,
        id=cfg["follower_id"],
        disable_torque_on_disconnect=False,
        max_relative_target=args.max_relative_target,
        cameras={},
        use_degrees=True,
    )
    robot = SOFollower(robot_cfg)
    robot.connect(calibrate=False)

    try:
        obs = robot.get_observation()
        current_pose = {motor: float(obs[f"{motor}.pos"]) for motor in MOTOR_ORDER}
        target_pose = dict(DEFAULT_TARGET)

        if args.skip_wrist_roll:
            target_pose["wrist_roll"] = current_pose["wrist_roll"]
        else:
            target_pose["wrist_roll"] = nearest_equivalent(
                target_pose["wrist_roll"], current_pose["wrist_roll"]
            )

        print("Current pose")
        print(format_pose(current_pose))
        print("\nTarget pose")
        print(format_pose(target_pose))
        print()

        for step in range(1, args.steps + 1):
            obs = robot.get_observation()
            current_pose = {motor: float(obs[f"{motor}.pos"]) for motor in MOTOR_ORDER}
            deltas = {motor: target_pose[motor] - current_pose[motor] for motor in MOTOR_ORDER}

            max_abs_delta = max(abs(delta) for delta in deltas.values())
            print(f"Step {step}/{args.steps} max_abs_delta={max_abs_delta:.2f}")
            print(format_pose(current_pose))
            print()

            if max_abs_delta <= args.tolerance:
                print("Pose is close enough to target.")
                break

            action = {f"{motor}.pos": target_pose[motor] for motor in MOTOR_ORDER}
            robot.send_action(action)
            time.sleep(args.settle_s)
        else:
            print("Reached maximum steps before fully converging.")

        final_obs = robot.get_observation()
        final_pose = {motor: float(final_obs[f"{motor}.pos"]) for motor in MOTOR_ORDER}
        print("\nFinal pose")
        print(format_pose(final_pose))

    finally:
        robot.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
