#!/usr/bin/env python3
"""Pure pre-close pose checks for the calibrated tray-centre orange grasp.

The wrist camera can reproduce the successful 2-D image while the gripper is
nearly 20 mm away in 3-D.  This module makes the measured robot pose an
independent, mandatory condition for any tray close.  It never connects to or
moves the robot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from generate_tray_cartesian_path import DEFAULT_URDF, Kinematics


SUCCESSFUL_GRASP_Q = np.array([74.5, -64.6, 83.2, 40.8, 0.0], dtype=float)
MAX_CARTESIAN_ERROR_MM = 3.0
MAX_JOINT_ERROR_DEG = 3.0
KINEMATICS = Kinematics(DEFAULT_URDF)
SUCCESSFUL_GRASP_XYZ_MM = KINEMATICS.fk(SUCCESSFUL_GRASP_Q)[:3, 3] * 1000


@dataclass(frozen=True)
class PoseGuardResult:
    result: str
    safe_pose_for_close: bool
    measured_q: list[float]
    reference_q: list[float]
    joint_error_deg: list[float]
    max_joint_error_deg: float
    measured_xyz_mm: list[float]
    reference_xyz_mm: list[float]
    cartesian_error_mm: list[float]
    cartesian_distance_mm: float
    joint_tolerance_deg: float
    cartesian_tolerance_mm: float

    def as_dict(self) -> dict:
        return asdict(self)


def evaluate_pose(
    measured_q: np.ndarray | list[float],
    *,
    joint_tolerance_deg: float = MAX_JOINT_ERROR_DEG,
    cartesian_tolerance_mm: float = MAX_CARTESIAN_ERROR_MM,
) -> PoseGuardResult:
    measured_q = np.asarray(measured_q, dtype=float)
    if measured_q.shape not in {(5,), (6,)}:
        raise ValueError(f"expected five arm joints, optionally gripper; got {measured_q.shape}")
    arm_q = measured_q[:5]
    measured_xyz_mm = KINEMATICS.fk(arm_q)[:3, 3] * 1000
    joint_error = arm_q - SUCCESSFUL_GRASP_Q
    cartesian_error = measured_xyz_mm - SUCCESSFUL_GRASP_XYZ_MM
    max_joint_error = float(np.max(np.abs(joint_error)))
    cartesian_distance = float(np.linalg.norm(cartesian_error))
    passed = bool(
        max_joint_error <= joint_tolerance_deg
        and cartesian_distance <= cartesian_tolerance_mm
    )
    return PoseGuardResult(
        result="PASS" if passed else "REJECT",
        safe_pose_for_close=passed,
        measured_q=arm_q.round(4).tolist(),
        reference_q=SUCCESSFUL_GRASP_Q.tolist(),
        joint_error_deg=joint_error.round(4).tolist(),
        max_joint_error_deg=round(max_joint_error, 4),
        measured_xyz_mm=measured_xyz_mm.round(3).tolist(),
        reference_xyz_mm=SUCCESSFUL_GRASP_XYZ_MM.round(3).tolist(),
        cartesian_error_mm=cartesian_error.round(3).tolist(),
        cartesian_distance_mm=round(cartesian_distance, 3),
        joint_tolerance_deg=joint_tolerance_deg,
        cartesian_tolerance_mm=cartesian_tolerance_mm,
    )

