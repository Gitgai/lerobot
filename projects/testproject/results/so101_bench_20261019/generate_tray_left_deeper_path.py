#!/usr/bin/env python3
"""Generate bounded deeper candidates for the unverified tray-left grasp.

This tool is offline only.  The robot URDF does not model the tray, so these
candidates pass kinematic and motion-envelope checks but still require an
open-gripper, empty-tray, watched dry run before any grasp attempt.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from generate_tray_cartesian_path import DEFAULT_URDF, HERE, Kinematics


DEFAULT_OUTPUT = HERE / "reset/kinematics/tray_left_deeper_path.json"
START_Q = np.array([57.7, -64.6, 83.2, 40.8, 0.0], dtype=float)
CENTRE_HOVER_Q = np.array([74.5, -68.4, 86.8, 42.4, 0.0], dtype=float)
ENV_MIN = np.array([-111.4, -104.9, -92.0, -99.6, -75.3], dtype=float) - 5
ENV_MAX = np.array([84.0, 82.9, 97.3, 103.1, 90.9], dtype=float) + 5


def generate(urdf: Path, maximum_depth_mm: int = 6) -> dict:
    model = Kinematics(urdf)
    start_xyz = model.fk(START_Q)[:3, 3]
    centre_hover_xyz = model.fk(CENTRE_HOVER_Q)[:3, 3]
    seed = START_Q.copy()
    candidates = []
    previous_q = START_Q.copy()
    for depth_mm in range(0, maximum_depth_mm + 1):
        target_xyz = start_xyz + np.array([0.0, 0.0, -depth_mm / 1000])
        seed = model.solve_position(seed, target_xyz)
        xyz = model.fk(seed)[:3, 3]
        candidates.append(
            {
                "depth_below_rejected_final_mm": depth_mm,
                "q": [round(float(value), 4) for value in seed],
                "xyz_mm": [round(float(value), 3) for value in xyz * 1000],
                "xy_drift_mm": round(float(np.linalg.norm((xyz - start_xyz)[:2]) * 1000), 3),
                "joint_step_max_deg": round(float(np.abs(seed - previous_q).max()), 3),
                "height_above_centre_hover_tool_z_mm": round(
                    float((xyz[2] - centre_hover_xyz[2]) * 1000), 3
                ),
            }
        )
        previous_q = seed.copy()
    return {
        "schema_version": 1,
        "generated_by": Path(__file__).name,
        "urdf": str(urdf.relative_to(HERE)),
        "safety_status": "EMPTY_TRAY_DRY_RUNS_PASSED_WATCHED_GRASP_REJECTED",
        "approved_for_tray_use": False,
        "source_attempt": "calibration_evidence/tray_left_guarded_hold_miss_20261105",
        "start_q": START_Q.tolist(),
        "start_xyz_mm": [round(float(value), 3) for value in start_xyz * 1000],
        "centre_hover_tool_z_mm": round(float(centre_hover_xyz[2] * 1000), 3),
        "maximum_candidate_depth_mm": maximum_depth_mm,
        "candidates": candidates,
        "constraints": {
            "pan_and_roll_fixed": True,
            "horizontal_target_fixed": True,
            "candidate_spacing_mm": 1,
            "maximum_joint_step_deg": 1.0,
            "maximum_horizontal_fk_drift_mm": 0.05,
            "must_remain_inside_demo_motion_envelope_plus_5_deg": True,
        },
        "dry_run_requirements": {
            "remove_orange_from_tray": True,
            "keep_tray_in_taped_position": True,
            "gripper_open": 37.0,
            "advance_one_candidate_at_a_time": True,
            "inspect_top_and_wrist_images_after_every_1mm_step": True,
            "stop_on_any_tray_contact_or_shift": True,
            "no_close_command": True,
            "reverse_same_candidates_to_retreat": True,
        },
        "physical_validation": {
            "empty_tray_runs": [
                {
                    "pan_deg": 57.7,
                    "result": "passed all 0-6 mm candidates without visible tray contact or shift",
                    "evidence": "calibration_evidence/tray_left_deeper_empty_dry_20261105",
                },
                {
                    "pan_deg": 60.7,
                    "result": "passed all 0-6 mm candidates without visible tray contact or shift",
                    "evidence": "calibration_evidence/tray_left_pan607_deeper_empty_dry_20261105",
                },
            ],
            "watched_grasp": {
                "pan_deg": 60.7,
                "stall": 5.9,
                "maximum_arm_drift_deg": 0.7,
                "result": "rejected miss; orange shifted about 35 pixels",
                "evidence": "calibration_evidence/tray_left_pan607_deeper_hold_miss_20261105",
            },
        },
        "blocker": "watched grasp missed; no tray-left operational waypoint is approved",
    }


def verify(data: dict) -> None:
    if data.get("approved_for_tray_use") is not False:
        raise ValueError("new path must remain blocked for tray use")
    candidates = data["candidates"]
    expected = list(range(data["maximum_candidate_depth_mm"] + 1))
    actual = [row["depth_below_rejected_final_mm"] for row in candidates]
    if actual != expected:
        raise ValueError(f"unexpected depths: {actual}")
    if max(row["xy_drift_mm"] for row in candidates) > 0.05:
        raise ValueError("horizontal FK drift exceeds 0.05 mm")
    if max(row["joint_step_max_deg"] for row in candidates) > 1.0:
        raise ValueError("a candidate joint step exceeds 1 degree")
    for row in candidates:
        q = np.asarray(row["q"])
        if np.any(q < ENV_MIN) or np.any(q > ENV_MAX):
            raise ValueError(f"candidate outside motion envelope: {row}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", type=Path, default=DEFAULT_URDF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--maximum-depth-mm", type=int, default=6)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        data = json.loads(args.output.read_text())
        verify(data)
        print(f"verified {args.output}")
        return
    data = generate(args.urdf.resolve(), args.maximum_depth_mm)
    verify(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
