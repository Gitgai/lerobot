#!/usr/bin/env python3
"""Generate and verify the tray-centre Cartesian lift/descent calibration path.

This is an offline kinematics tool.  It never connects to the robot.  The
generated path is calibration evidence only until its JSON explicitly says
``approved_for_tray_use: true``.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


HERE = Path(__file__).resolve().parent
DEFAULT_URDF = HERE / "reset/kinematics/so101_new_calib.urdf"
DEFAULT_OUTPUT = HERE / "reset/kinematics/tray_center_cartesian_path.json"
CHAIN = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper_frame_joint",
]
MOVING = CHAIN[:5]
HOVER_Q = np.array([77.2, -68.4, 86.8, 42.4, 0.0], dtype=float)


def rotation_xyz(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ]
    )


def transform(rotation: np.ndarray | None = None, translation: np.ndarray | None = None) -> np.ndarray:
    result = np.eye(4)
    if rotation is not None:
        result[:3, :3] = rotation
    if translation is not None:
        result[:3, 3] = translation
    return result


def axis_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    c, s, one_minus_c = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return np.array(
        [
            [x * x * one_minus_c + c, x * y * one_minus_c - z * s, x * z * one_minus_c + y * s],
            [y * x * one_minus_c + z * s, y * y * one_minus_c + c, y * z * one_minus_c - x * s],
            [z * x * one_minus_c - y * s, z * y * one_minus_c + x * s, z * z * one_minus_c + c],
        ]
    )


class Kinematics:
    def __init__(self, urdf: Path):
        root = ET.parse(urdf).getroot()
        self.joints = {joint.attrib["name"]: joint for joint in root.findall("joint")}

    def fk(self, q_degrees: np.ndarray) -> np.ndarray:
        pose = np.eye(4)
        for name in CHAIN:
            joint = self.joints[name]
            origin = joint.find("origin")
            xyz = np.fromstring(origin.attrib.get("xyz", "0 0 0"), sep=" ")
            rpy = np.fromstring(origin.attrib.get("rpy", "0 0 0"), sep=" ")
            pose = pose @ transform(rotation_xyz(*rpy), xyz)
            if name in MOVING:
                axis = np.fromstring(joint.find("axis").attrib["xyz"], sep=" ")
                angle = math.radians(q_degrees[MOVING.index(name)])
                pose = pose @ transform(axis_rotation(axis, angle))
        return pose

    def solve_position(self, seed: np.ndarray, target_xyz: np.ndarray) -> np.ndarray:
        q = seed.copy()
        active = [1, 2, 3]  # keep pan and roll fixed
        for _ in range(100):
            position = self.fk(q)[:3, 3]
            error = target_xyz - position
            if np.linalg.norm(error) < 1e-6:
                return q
            jacobian = np.zeros((3, 3))
            step_degrees = 0.02
            for column, index in enumerate(active):
                probe = q.copy()
                probe[index] += step_degrees
                jacobian[:, column] = (self.fk(probe)[:3, 3] - position) / step_degrees
            delta = np.linalg.solve(jacobian.T @ jacobian + 1e-6 * np.eye(3), jacobian.T @ error)
            q[active] += np.clip(delta, -1.0, 1.0)
        raise RuntimeError("inverse kinematics did not converge")


def generate(urdf: Path) -> dict:
    model = Kinematics(urdf)
    hover_xyz = model.fk(HOVER_Q)[:3, 3]
    seed = HOVER_Q.copy()
    waypoints = []
    for offset_mm in range(0, 41, 5):
        seed = model.solve_position(seed, hover_xyz + np.array([0.0, 0.0, offset_mm / 1000]))
        xyz = model.fk(seed)[:3, 3]
        waypoints.append(
            {
                "z_offset_mm": offset_mm,
                "q": [round(float(value), 4) for value in seed],
                "xyz_mm": [round(float(value), 3) for value in xyz * 1000],
                "xy_drift_mm": round(float(np.linalg.norm((xyz - hover_xyz)[:2]) * 1000), 3),
            }
        )
    return {
        "schema_version": 1,
        "generated_by": Path(__file__).name,
        "urdf": str(urdf.relative_to(HERE)),
        "urdf_source": "https://github.com/TheRobotStudio/SO-ARM100/blob/main/Simulation/SO101/so101_new_calib.urdf",
        "safety_status": "EMPTY_WORKSPACE_TEST_ONLY",
        "approved_for_tray_use": False,
        "hover_q": HOVER_Q.tolist(),
        "hover_xyz_mm": [round(float(value), 3) for value in hover_xyz * 1000],
        "direction": "waypoints ascend from verified centre hover; reverse them to descend",
        "waypoints": waypoints,
        "runtime_guard_requirements": {
            "max_joint_tracking_error_deg": 3.5,
            "max_horizontal_fk_error_mm": 5.0,
            "minimum_tool_z_during_tray_pan_mm": 33.5,
            "minimum_height_above_verified_hover_mm": 29.9,
            "require_live_fk_clearance_guard_during_tray_pan": True,
            "stop_on_error": True,
            "require_operator_watch": True,
            "do_not_use_bench_reset_yet": True,
        },
        "empty_workspace_test_20261105": {
            "result": "passed without reversal or large lateral sweep",
            "tray_present": False,
            "maximum_descent_horizontal_error_mm": 4.8,
            "maximum_ascent_horizontal_error_mm": 2.56,
            "lowest_actual_height_above_verified_hover_mm": 6.7,
            "raised_actual_q": [77.1, -71.6, 75.1, 58.6, -0.2, 44.8],
            "raised_actual_xyz_mm": [68.97, -131.5, 31.24],
            "note": "Elbow lag was load-dependent (about 1 to 3.3 deg); the path still needs a watched high-clearance tray dry run.",
        },
        "high_clearance_tray_test_20261105": {
            "result": "no contact, but rejected for insufficient maintained clearance",
            "descent_attempted": False,
            "tool_z_before_pan_mm": 31.39,
            "height_above_verified_hover_before_pan_mm": 27.81,
            "tool_z_after_pan_mm": 26.4,
            "height_above_verified_hover_after_pan_mm": 22.82,
            "tray_centre_before_px": [152.5, 129.5],
            "tray_centre_after_px": [152.0, 129.5],
            "tray_shift_px": 0.5,
            "approved_for_descent": False,
            "blocker": "the pass started below the 33.5 mm absolute-z guard (about 30 mm above hover), then elbow relaxation reduced height further",
        },
        "guarded_40mm_tray_test_20261105": {
            "high_pan_result": "passed live 33.5 mm absolute-z guard without tray contact",
            "tool_z_before_pan_mm": 44.73,
            "height_above_verified_hover_before_pan_mm": 41.15,
            "tool_z_after_pan_mm": 40.33,
            "height_above_verified_hover_after_pan_mm": 36.75,
            "descent_result": "stopped and rejected at nominal 20 mm waypoint",
            "actual_stop_xyz_mm": [68.37, -127.87, 18.6],
            "actual_height_above_verified_hover_mm": 15.02,
            "horizontal_fk_error_mm": 5.25,
            "gripper_close_attempted": False,
            "tray_contour_centroid_shift_px": 0.2,
            "orange_shift_px": 13.6,
            "approved_for_descent": False,
            "blocker": "open-loop joint tracking error exceeded the 5 mm horizontal limit and the open gripper shifted the fruit",
        },
        "closed_loop_descent_test_20261105": {
            "control_result": "reduced horizontal error at nominal 20 mm from 5.25 mm to 0.76 mm",
            "open_finger_alignment_pan_deg": 70.0,
            "alignment_note": "79.9 deg moved the fixed finger farther into the orange image; 70 deg centred this shifted fruit while open",
            "approach_method": "four measured substeps from hover to the prior centre approach geometry",
            "close_command": 15.0,
            "close_actual": 15.1,
            "close_result": "miss; one finger against fruit and opposite finger clear",
            "orange_shift_px": 9.2,
            "tray_detector_shift_px": 6.7,
            "grasp_verified": False,
            "approved_for_descent": False,
            "blocker": "open-finger visual centring did not predict the jaw centre after closure",
        },
        "closed_loop_centre_success_20261105": {
            "centre_path_verified": True,
            "pan_deg": 74.5,
            "final_approach_q": [74.5, -64.6, 83.2, 40.8, 0.0, 37.0],
            "close_method": "2-unit close-on-stall steps",
            "grasp_stall": 21.9,
            "accepted_hold_range": [16.0, 26.0],
            "lift_verified": True,
            "sideways_carry_deg": 3.0,
            "carry_verified": True,
            "release_into_tray_verified": True,
            "arm_returned_home": True,
            "torque_disabled": True,
            "evidence_dir": "reset/calibration_evidence/tray_closed_loop_success_20261105",
            "auto_reset_approved": False,
            "remaining_blocker": "left, right, near and far tray descents remain unverified",
        },
    }


def verify(data: dict) -> None:
    offsets = [row["z_offset_mm"] for row in data["waypoints"]]
    if offsets != list(range(0, 41, 5)):
        raise ValueError(f"unexpected offsets: {offsets}")
    max_drift = max(row["xy_drift_mm"] for row in data["waypoints"])
    if max_drift > 0.05:
        raise ValueError(f"nominal horizontal drift is {max_drift} mm")
    if data.get("approved_for_tray_use") is not False:
        raise ValueError("newly generated path must remain blocked for tray use")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", type=Path, default=DEFAULT_URDF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="verify an existing output without rewriting it")
    args = parser.parse_args()
    if args.check:
        data = json.loads(args.output.read_text())
        verify(data)
        print(f"verified {args.output}")
        return
    data = generate(args.urdf.resolve())
    verify(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
