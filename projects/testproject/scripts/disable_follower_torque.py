#!/usr/bin/env python3
"""Disable torque on the serial-identified SO-101 follower."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "so101.json"
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def main() -> int:
    with CONFIG_PATH.open() as config_file:
        config = json.load(config_file)

    port = Path(config["follower_serial"])
    if not port.exists():
        print(f"follower serial path is unavailable: {port}", file=sys.stderr)
        return 2

    motors = {joint: Motor(i + 1, "sts3215", MotorNormMode.RANGE_M100_100) for i, joint in enumerate(JOINTS)}
    bus = FeetechMotorsBus(port=str(port), motors=motors)
    try:
        bus.connect(handshake=False)
        before = bus.sync_read("Torque_Enable", normalize=False)
        bus.disable_torque()
        after = bus.sync_read("Torque_Enable", normalize=False)
        print("follower torque before:", " ".join(f"{j}={'ON' if before[j] else 'off'}" for j in JOINTS))
        print("follower torque after: ", " ".join(f"{j}={'ON' if after[j] else 'off'}" for j in JOINTS))
        return 0 if not any(after.values()) else 3
    finally:
        try:
            bus.disconnect(disable_torque=False)
        except Exception as exc:
            print(f"WARNING: follower bus disconnect failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
