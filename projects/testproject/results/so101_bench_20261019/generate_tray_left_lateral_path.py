#!/usr/bin/env python3
"""Generate a bounded tray-left lateral arc from measured wrist-image error.

This tool is offline only.  It converts the measured wrist offset through the
observed pan-to-pixel response, then emits half-degree candidates around the
estimated correction.  The URDF has no tray collision geometry, so the output
remains blocked until an open-gripper, empty-tray watched dry run passes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from generate_tray_cartesian_path import DEFAULT_URDF, HERE, Kinematics


DEFAULT_OUTPUT = HERE / "reset/kinematics/tray_left_lateral_path.json"
START_Q = np.array([60.7, -63.5184, 85.8777, 36.4823, 0.0], dtype=float)
OBSERVED_OFFSET_PX = 45.0
TARGET_OFFSET_PX = -5.0
PIXELS_PER_PAN_DEG = -12.5
PAN_STEP_DEG = 0.5
EXTRA_MARGIN_DEG = 0.5
ENV_MIN = np.array([-111.4, -104.9, -92.0, -99.6, -75.3], dtype=float) - 5
ENV_MAX = np.array([84.0, 82.9, 97.3, 103.1, 90.9], dtype=float) + 5


def generate(urdf: Path) -> dict:
    model = Kinematics(urdf)
    start_xyz = model.fk(START_Q)[:3, 3]
    correction_deg = (TARGET_OFFSET_PX - OBSERVED_OFFSET_PX) / PIXELS_PER_PAN_DEG
    estimated_pan_deg = float(START_Q[0] + correction_deg)
    final_pan_deg = estimated_pan_deg + EXTRA_MARGIN_DEG
    pans = np.arange(START_Q[0], final_pan_deg + PAN_STEP_DEG / 2, PAN_STEP_DEG)
    candidates = []
    previous_q = START_Q.copy()
    for pan_deg in pans:
        q = START_Q.copy()
        q[0] = pan_deg
        xyz = model.fk(q)[:3, 3]
        candidates.append(
            {
                "pan_deg": round(float(pan_deg), 3),
                "q": [round(float(value), 4) for value in q],
                "xyz_mm": [round(float(value), 3) for value in xyz * 1000],
                "horizontal_shift_from_start_mm": round(
                    float(np.linalg.norm((xyz - start_xyz)[:2]) * 1000), 3
                ),
                "tool_z_change_from_start_mm": round(float((xyz[2] - start_xyz[2]) * 1000), 3),
                "joint_step_max_deg": round(float(np.abs(q - previous_q).max()), 3),
                "predicted_wrist_offset_px": round(
                    float(
                        OBSERVED_OFFSET_PX
                        + PIXELS_PER_PAN_DEG * (pan_deg - START_Q[0])
                    ),
                    2,
                ),
            }
        )
        previous_q = q
    return {
        "schema_version": 1,
        "generated_by": Path(__file__).name,
        "urdf": str(urdf.relative_to(HERE)),
        "safety_status": "EMPTY_TRAY_DRY_RUN_PASSED_WATCHED_GRASP_REJECTED",
        "approved_for_tray_use": False,
        "source_attempt": "calibration_evidence/tray_left_pan607_deeper_hold_miss_20261105",
        "source_pan_response": {
            "evidence": "calibration_evidence/tray_left_guarded_alignment_miss_20261105",
            "observed_pixels_per_pan_degree": PIXELS_PER_PAN_DEG,
        },
        "offset_model": {
            "observed_offset_px": OBSERVED_OFFSET_PX,
            "target_offset_px": TARGET_OFFSET_PX,
            "estimated_correction_deg": round(float(correction_deg), 3),
            "estimated_pan_deg": round(estimated_pan_deg, 3),
        },
        "start_q": START_Q.tolist(),
        "candidate_step_deg": PAN_STEP_DEG,
        "candidates": candidates,
        "constraints": {
            "lift_elbow_wrist_flex_roll_fixed": True,
            "maximum_joint_step_deg": PAN_STEP_DEG,
            "maximum_tool_z_change_mm": 0.05,
            "must_remain_inside_demo_motion_envelope_plus_5_deg": True,
        },
        "dry_run_requirements": {
            "remove_orange_from_tray": True,
            "keep_tray_in_taped_position": True,
            "gripper_open": 37.0,
            "reach_deep_start_through_verified_vertical_path": True,
            "advance_one_candidate_at_a_time": True,
            "inspect_top_and_wrist_images_after_every_step": True,
            "stop_on_any_tray_contact_or_shift": True,
            "no_close_command": True,
            "reverse_same_candidates_to_retreat": True,
        },
        "physical_validation": {
            "empty_tray_run": {
                "result": "passed all candidates without visible tray contact or shift",
                "maximum_commanded_pan_deg": 65.2,
                "maximum_measured_pan_deg": 64.8,
                "evidence": "calibration_evidence/tray_left_lateral_empty_dry_20261105",
            },
            "watched_grasp": {
                "selected_commanded_pan_deg": 63.2,
                "selected_measured_pan_deg": 63.0,
                "selected_wrist_offset_px": -3.0,
                "stall": 7.4,
                "maximum_arm_drift_deg": 1.4,
                "result": "rejected miss; lateral alignment corrected but front/back closing plane remained wrong",
                "evidence": "calibration_evidence/tray_left_lateral_hold_miss_20261105",
            },
        },
        "blocker": "watched grasp missed; front/back Cartesian correction remains unverified",
    }


def verify(data: dict) -> None:
    if data.get("approved_for_tray_use") is not False:
        raise ValueError("new path must remain blocked for tray use")
    candidates = data["candidates"]
    if candidates[0]["q"] != data["start_q"]:
        raise ValueError("first candidate must equal the measured start pose")
    if max(row["joint_step_max_deg"] for row in candidates) > PAN_STEP_DEG:
        raise ValueError("candidate joint step exceeds bound")
    if max(abs(row["tool_z_change_from_start_mm"]) for row in candidates) > 0.05:
        raise ValueError("tool z changed during lateral arc")
    for row in candidates:
        q = np.asarray(row["q"])
        if np.any(q < ENV_MIN) or np.any(q > ENV_MAX):
            raise ValueError(f"candidate outside motion envelope: {row}")


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
