#!/usr/bin/env python3
"""Generate bounded two-sided front/back candidates for tray-left grasping.

The selected lateral pose centres the orange in wrist x but leaves a large
wrist-y error.  This offline tool holds pan, roll and tool z fixed, and solves
two local planar Cartesian branches so a watched image check can determine
which front/back direction reduces that error.  The generated candidates have
passed an open-gripper empty-tray dry run, but remain blocked until a watched
orange alignment and grasp/lift test selects an operational offset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from generate_tray_cartesian_path import DEFAULT_URDF, HERE, Kinematics


DEFAULT_OUTPUT = HERE / "reset/kinematics/tray_left_front_back_path.json"
START_Q = np.array([63.2, -63.5184, 85.8777, 36.4823, 0.0], dtype=float)
STEP_MM = 1
MAXIMUM_OFFSET_MM = 12
ENV_MIN = np.array([-111.4, -104.9, -92.0, -99.6, -75.3], dtype=float) - 5
ENV_MAX = np.array([84.0, 82.9, 97.3, 103.1, 90.9], dtype=float) + 5


def make_branch(
    model: Kinematics,
    start_xyz: np.ndarray,
    front_back_xy: np.ndarray,
    sign: int,
) -> list[dict]:
    seed = START_Q.copy()
    previous_q = START_Q.copy()
    rows = []
    for offset_mm in range(0, MAXIMUM_OFFSET_MM + STEP_MM, STEP_MM):
        target = start_xyz.copy()
        target[:2] += sign * front_back_xy * offset_mm / 1000
        seed = model.solve_position(seed, target)
        xyz = model.fk(seed)[:3, 3]
        rows.append(
            {
                "offset_mm": sign * offset_mm,
                "q": [round(float(value), 4) for value in seed],
                "xyz_mm": [round(float(value), 3) for value in xyz * 1000],
                "horizontal_error_mm": round(
                    float(np.linalg.norm((xyz - target)[:2]) * 1000), 3
                ),
                "tool_z_change_mm": round(float((xyz[2] - start_xyz[2]) * 1000), 3),
                "joint_step_max_deg": round(float(np.abs(seed - previous_q).max()), 3),
            }
        )
        previous_q = seed.copy()
    return rows


def generate(urdf: Path) -> dict:
    model = Kinematics(urdf)
    start_xyz = model.fk(START_Q)[:3, 3]
    probe = START_Q.copy()
    probe[2] += 0.01
    horizontal_derivative = (model.fk(probe)[:3, 3] - start_xyz)[:2]
    front_back_xy = horizontal_derivative / np.linalg.norm(horizontal_derivative)
    positive = make_branch(model, start_xyz, front_back_xy, 1)
    negative = make_branch(model, start_xyz, front_back_xy, -1)
    return {
        "schema_version": 1,
        "generated_by": Path(__file__).name,
        "urdf": str(urdf.relative_to(HERE)),
        "safety_status": "PHYSICAL_CLEARANCE_PASSED_ALIGNMENT_MODEL_REJECTED",
        "approved_for_tray_use": False,
        "source_attempt": "calibration_evidence/tray_left_lateral_hold_miss_20261105",
        "start_q": START_Q.tolist(),
        "start_xyz_mm": [round(float(value), 3) for value in start_xyz * 1000],
        "front_back_unit_xy": [round(float(value), 6) for value in front_back_xy],
        "candidate_step_mm": STEP_MM,
        "maximum_offset_mm": MAXIMUM_OFFSET_MM,
        "branches": {
            "positive_local_front_back": positive,
            "negative_local_front_back": negative,
        },
        "constraints": {
            "pan_and_roll_fixed": True,
            "tool_z_fixed": True,
            "maximum_joint_step_deg": 2.0,
            "maximum_horizontal_ik_error_mm": 0.05,
            "maximum_tool_z_error_mm": 0.05,
            "must_remain_inside_demo_motion_envelope_plus_5_deg": True,
        },
        "dry_run_requirements": {
            "remove_orange_from_tray": True,
            "keep_tray_in_taped_position": True,
            "gripper_open": 37.0,
            "reach_selected_lateral_start_through_verified_paths": True,
            "test_positive_branch_then_reverse_to_start": True,
            "test_negative_branch_then_reverse_to_start": True,
            "advance_one_candidate_at_a_time": True,
            "inspect_top_and_wrist_images_after_every_step": True,
            "stop_on_any_tray_contact_or_shift": True,
            "no_close_command": True,
        },
        "watched_alignment_plan": {
            "start_at_offset_mm": 0,
            "measure_orange_wrist_y_at_each_safe_candidate": True,
            "select_direction_only_if_wrist_y_moves_toward_verified_centre_reference": True,
            "close_only_after_symmetric_finger_clearance_and_improved_wrist_y": True,
        },
        "physical_validation": {
            "date": "2026-11-05",
            "evidence_dir": "calibration_evidence/tray_left_front_back_empty_dry_20261105",
            "tray_empty": True,
            "gripper_open": 37.0,
            "candidate_spacing_mm": 1,
            "positive_branch_tested_mm": [0, 12],
            "negative_branch_tested_mm": [-12, 0],
            "top_and_wrist_images_inspected_after_every_outbound_step": True,
            "positive_branch_returned_to_start": True,
            "negative_branch_returned_to_start": True,
            "tray_contact_observed": False,
            "tray_shift_observed": False,
            "arm_returned_home": True,
            "torque_disabled": True,
            "result": "pass for open-gripper clearance only",
            "watched_alignment_20261105": {
                "placement_top_px": [135.7, 137.2],
                "calibrated_tray_centre_px": [150.0, 143.5],
                "reset_classifier_region": "centre",
                "wrist_orange_centre_at_offset_0_px": [385.0, 118.7],
                "wrist_orange_centre_at_offset_minus_12_px": [393.5, 149.1],
                "successful_reference_px": [325.2, 165.9],
                "wrist_flex_change_deg": -11.4,
                "wrist_link_origin_z_at_minus_12_mm": 136.4,
                "gripper_body_origin_z_at_minus_12_mm": 87.8,
                "jaw_tip_frame_z_at_minus_12_mm": 5.0,
                "maximum_observed_tray_border_shift_px": 1.3,
                "two_cm_wrist_clearance_satisfied": True,
                "close_attempted": False,
                "result": "rejected: corrected wrist y but worsened wrist x and changed gripper orientation",
                "arm_returned_home": True,
                "torque_disabled": True,
                "evidence_dir": "calibration_evidence/tray_left_front_back_alignment_rejected_20261105",
            },
        },
        "blocker": "position-only IK changes gripper orientation; replace with coupled two-axis fixed-orientation visual alignment",
    }


def verify(data: dict) -> None:
    if data.get("approved_for_tray_use") is not False:
        raise ValueError("new path must remain blocked for tray use")
    for name, rows in data["branches"].items():
        if rows[0]["offset_mm"] != 0 or rows[0]["q"] != data["start_q"]:
            raise ValueError(f"{name} does not start at the measured pose")
        if max(row["joint_step_max_deg"] for row in rows) > 2.0:
            raise ValueError(f"{name} joint step exceeds 2 degrees")
        if max(row["horizontal_error_mm"] for row in rows) > 0.05:
            raise ValueError(f"{name} horizontal IK error exceeds bound")
        if max(abs(row["tool_z_change_mm"]) for row in rows) > 0.05:
            raise ValueError(f"{name} tool z changed")
        for row in rows:
            q = np.asarray(row["q"])
            if np.any(q < ENV_MIN) or np.any(q > ENV_MAX):
                raise ValueError(f"{name} candidate outside motion envelope: {row}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", type=Path, default=DEFAULT_URDF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
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
