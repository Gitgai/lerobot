#!/usr/bin/env python3
"""Dry-run or execute a guarded empty-workspace restore to the U1 start pose.

The script never connects to a policy.  Dry-run is the default.  Live execution
requires ``--execute`` and refuses a start more than 10 units from the target.
Torque is disabled on every exit path.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

from lerobot.motors import Motor, MotorCalibration, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from generate_tray_cartesian_path import DEFAULT_URDF, Kinematics  # noqa: E402

JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
TARGET = np.array([-7.8, -104.0, 96.7, 78.3, -1.3, 51.3], dtype=float)
ENVELOPE_MIN = np.array([-111.4, -104.9, -92.0, -99.6, -75.3, 1.6], dtype=float) - 5.0
ENVELOPE_MAX = np.array([84.0, 82.9, 97.3, 103.1, 90.9, 88.2], dtype=float) + 5.0
STEP_LIMIT = np.array([0.3] * 5 + [0.75], dtype=float)
PROBE_OFFSET = np.array([0, 0, 0, 0, 1.0, 0], dtype=float)
PROTECTIONS = {"Max_Torque_Limit": 500, "Protection_Current": 250, "Overload_Torque": 25}
DEFAULT_PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B14114209-if00"
DEFAULT_CALIBRATION = Path(
    "/home/gaikwad-prakash/.cache/huggingface/lerobot/calibration/robots/so_follower/my_so101_follower.json"
)
CAMERAS = {
    "front": "/dev/v4l/by-id/usb-046d_C270_HD_WEBCAM_FC7A6780-video-index0",
    "wrist": "/dev/v4l/by-id/usb-SunplusIT_Inc_AK-Camera_JV-video-index0",
}


def load_calibration(path: Path) -> dict[str, MotorCalibration]:
    raw = json.loads(path.read_text())
    return {name: MotorCalibration(**values) for name, values in raw.items()}


def make_bus(port: str, calibration: dict[str, MotorCalibration]) -> FeetechMotorsBus:
    motors = {
        name: Motor(index + 1, "sts3215", MotorNormMode.DEGREES if index < 5 else MotorNormMode.RANGE_0_100)
        for index, name in enumerate(JOINTS)
    }
    return FeetechMotorsBus(port=port, motors=motors, calibration=calibration)


def read_pose(bus: FeetechMotorsBus) -> np.ndarray:
    values = bus.sync_read("Present_Position", JOINTS)
    return np.array([float(values[name]) for name in JOINTS], dtype=float)


def interpolate(start: np.ndarray, target: np.ndarray) -> list[np.ndarray]:
    steps = max(1, int(np.ceil(np.max(np.abs(target - start) / STEP_LIMIT))))
    return [start + (target - start) * (index / steps) for index in range(1, steps + 1)]


def check_waypoints(waypoints: list[np.ndarray]) -> None:
    for index, waypoint in enumerate(waypoints, start=1):
        if np.any(waypoint < ENVELOPE_MIN) or np.any(waypoint > ENVELOPE_MAX):
            raise RuntimeError(f"waypoint {index} is outside the demonstrated envelope: {waypoint.tolist()}")


def capture_camera(device: str, output: Path) -> None:
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    frame = None
    for _ in range(45):
        ok, candidate = cap.read()
        if ok:
            frame = candidate
    cap.release()
    if frame is None:
        raise RuntimeError(f"could not capture camera {device}")
    if not cv2.imwrite(str(output), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise RuntimeError(f"could not save {output}")


def execute_leg(bus: FeetechMotorsBus, start: np.ndarray, target: np.ndarray, label: str, events: list[dict]) -> np.ndarray:
    waypoints = interpolate(start, target)
    check_waypoints(waypoints)
    for index, waypoint in enumerate(waypoints, start=1):
        bus.sync_write("Goal_Position", dict(zip(JOINTS, waypoint, strict=True)))
        time.sleep(1 / 30)
        measured = read_pose(bus)
        error = np.abs(measured - waypoint)
        if np.max(error[:5]) > 5.0 or error[5] > 8.0:
            raise RuntimeError(
                f"{label} tracking abort at waypoint {index}: max arm error {np.max(error[:5]):.2f}, "
                f"gripper error {error[5]:.2f}"
            )
    time.sleep(0.5)
    reached = read_pose(bus)
    events.append(
        {
            "event": "leg_complete",
            "label": label,
            "waypoint_count": len(waypoints),
            "target": target.round(4).tolist(),
            "reached": reached.round(4).tolist(),
            "error": (reached - target).round(4).tolist(),
        }
    )
    return reached


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Move the real arm; omission performs read-only dry-run.")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--report-dir", type=Path, default=HERE / "u1_start_restore_20261107")
    args = parser.parse_args()

    args.report_dir.mkdir(parents=True, exist_ok=True)
    calibration = load_calibration(args.calibration)
    report = {
        "captured_at": datetime.now().astimezone().isoformat(),
        "mode": "execute" if args.execute else "dry_run",
        "port": args.port,
        "calibration_path": str(args.calibration),
        "calibration_sha256": hashlib.sha256(args.calibration.read_bytes()).hexdigest(),
        "target": TARGET.tolist(),
        "step_limit": STEP_LIMIT.tolist(),
        "events": [],
    }
    bus = make_bus(args.port, calibration)
    bus.connect(handshake=False)
    try:
        torque = bus.sync_read("Torque_Enable", JOINTS, normalize=False)
        if any(int(torque[name]) != 0 for name in JOINTS):
            raise RuntimeError(f"refusing start because torque is already enabled: {torque}")
        start = read_pose(bus)
        report["start"] = start.round(4).tolist()
        report["start_delta_to_target"] = (TARGET - start).round(4).tolist()
        if np.max(np.abs(TARGET - start)) > 10.0:
            raise RuntimeError(f"start is more than 10 units from U1 target: {start.tolist()}")

        initial_path = interpolate(start, TARGET)
        repeat_out = interpolate(TARGET, TARGET + PROBE_OFFSET) + interpolate(TARGET + PROBE_OFFSET, TARGET)
        all_waypoints = initial_path + repeat_out + repeat_out
        check_waypoints(all_waypoints)
        kin = Kinematics(DEFAULT_URDF)
        xyz = np.array([kin.fk(waypoint[:5])[:3, 3] for waypoint in [start, *all_waypoints]])
        report["offline"] = {
            "initial_waypoint_count": len(initial_path),
            "total_waypoint_count": len(all_waypoints),
            "envelope_pass": True,
            "max_cartesian_displacement_from_start_mm": float(np.max(np.linalg.norm(xyz - xyz[0], axis=1)) * 1000),
            "minimum_relative_z_mm": float(np.min((xyz[:, 2] - xyz[0, 2]) * 1000)),
            "maximum_joint_step": np.max(np.abs(np.diff(np.array([start, *all_waypoints]), axis=0)), axis=0).round(4).tolist(),
        }
        if report["offline"]["max_cartesian_displacement_from_start_mm"] > 20.0:
            raise RuntimeError("offline Cartesian displacement exceeds 20 mm")
        if report["offline"]["minimum_relative_z_mm"] < -5.0:
            raise RuntimeError("offline path descends more than 5 mm")

        if args.execute:
            for register, value in PROTECTIONS.items():
                bus.write(register, "gripper", value, normalize=False)
            protection_readback = {
                register: int(bus.read(register, "gripper", normalize=False)) for register in PROTECTIONS
            }
            if protection_readback != PROTECTIONS:
                raise RuntimeError(f"gripper protection mismatch: {protection_readback}")
            report["protection_readback"] = protection_readback

            # Prevent a torque-on jump by making the current measured pose the goal first.
            bus.sync_write("Goal_Position", dict(zip(JOINTS, start, strict=True)))
            bus.enable_torque()
            reached = execute_leg(bus, start, TARGET, "return_1", report["events"])
            returns = [reached]
            for return_index in (2, 3):
                probe = execute_leg(bus, reached, TARGET + PROBE_OFFSET, f"probe_{return_index}", report["events"])
                reached = execute_leg(bus, probe, TARGET, f"return_{return_index}", report["events"])
                returns.append(reached)
            returns_array = np.array(returns)
            report["returns"] = returns_array.round(4).tolist()
            report["return_errors"] = (returns_array - TARGET).round(4).tolist()
            report["max_return_arm_error"] = float(np.max(np.abs(returns_array[:, :5] - TARGET[:5])))
            report["max_return_gripper_error"] = float(np.max(np.abs(returns_array[:, 5] - TARGET[5])))
            report["max_return_spread"] = np.ptp(returns_array, axis=0).round(4).tolist()
            if report["max_return_arm_error"] > 1.0 or report["max_return_gripper_error"] > 2.0:
                raise RuntimeError("U1 return acceptance tolerance failed")
            temperatures = bus.sync_read("Present_Temperature", JOINTS, normalize=False)
            voltages = bus.sync_read("Present_Voltage", JOINTS, normalize=False)
            report["final_health"] = {
                name: {"temperature_c": int(temperatures[name]), "voltage_v": int(voltages[name]) / 10}
                for name in JOINTS
            }
        report["result"] = "PASS" if args.execute else "DRY_RUN_PASS"
    except Exception as exc:
        report["result"] = "FAIL"
        report["error"] = str(exc)
        raise
    finally:
        try:
            bus.disable_torque()
        finally:
            bus.disconnect()
            (args.report_dir / ("execute_report.json" if args.execute else "dry_run_report.json")).write_text(
                json.dumps(report, indent=2) + "\n"
            )

    if args.execute:
        for name, device in CAMERAS.items():
            capture_camera(device, args.report_dir / f"final_{name}.jpg")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
