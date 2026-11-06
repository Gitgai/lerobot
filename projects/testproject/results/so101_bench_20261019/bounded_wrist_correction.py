#!/usr/bin/env python3
"""Check whether a wrist-image error is correctable inside a cleared envelope.

This module is offline/read-only.  It never connects to the robot.  The local
Jacobian is valid only inside the empty-tray-cleared final refinement region;
an unbounded solution is reported for diagnosis but is never approved.
"""

from __future__ import annotations

import argparse
import json
import math


DEFAULT_JACOBIAN = ((-4.26, 2.605), (-1.35, 3.70))
DEFAULT_GATE_PX = 5.0
DEFAULT_MAX_PAN_DEG = 1.0
DEFAULT_MAX_RADIAL_MM = 2.0


def solve_2x2(matrix: tuple[tuple[float, float], tuple[float, float]], rhs: tuple[float, float]):
    a, b = matrix[0]
    c, d = matrix[1]
    determinant = a * d - b * c
    if abs(determinant) < 1e-9:
        raise ValueError("singular wrist Jacobian")
    x = (rhs[0] * d - b * rhs[1]) / determinant
    y = (a * rhs[1] - rhs[0] * c) / determinant
    return x, y


def residual(error, jacobian, pan_deg, radial_mm):
    return (
        error[0] + jacobian[0][0] * pan_deg + jacobian[0][1] * radial_mm,
        error[1] + jacobian[1][0] * pan_deg + jacobian[1][1] * radial_mm,
    )


def evaluate(
    error: tuple[float, float],
    *,
    jacobian=DEFAULT_JACOBIAN,
    gate_px=DEFAULT_GATE_PX,
    max_pan_deg=DEFAULT_MAX_PAN_DEG,
    max_radial_mm=DEFAULT_MAX_RADIAL_MM,
    grid_step=0.025,
):
    unbounded = solve_2x2(jacobian, (-error[0], -error[1]))
    best = None
    pan_steps = round(2 * max_pan_deg / grid_step)
    radial_steps = round(2 * max_radial_mm / grid_step)
    for pan_index in range(pan_steps + 1):
        pan = -max_pan_deg + pan_index * grid_step
        for radial_index in range(radial_steps + 1):
            radial = -max_radial_mm + radial_index * grid_step
            remaining = residual(error, jacobian, pan, radial)
            norm = math.hypot(*remaining)
            candidate = (norm, abs(pan) + abs(radial), pan, radial, remaining)
            if best is None or candidate < best:
                best = candidate
    assert best is not None
    approved = abs(best[4][0]) <= gate_px and abs(best[4][1]) <= gate_px
    return {
        "input_error_px": [round(value, 3) for value in error],
        "cleared_envelope": {
            "max_abs_pan_deg": max_pan_deg,
            "max_abs_radial_mm": max_radial_mm,
            "gate_each_axis_px": gate_px,
        },
        "unbounded_zero_error_solution": {
            "pan_deg": round(unbounded[0], 3),
            "radial_mm": round(unbounded[1], 3),
            "inside_cleared_envelope": (
                abs(unbounded[0]) <= max_pan_deg and abs(unbounded[1]) <= max_radial_mm
            ),
        },
        "best_cleared_solution": {
            "pan_deg": round(best[2], 3),
            "radial_mm": round(best[3], 3),
            "predicted_residual_px": [round(value, 3) for value in best[4]],
        },
        "correctable_inside_cleared_envelope": approved,
        "decision": "ALLOW_LOCAL_REFINEMENT" if approved else "REFUSE_LOCAL_EXTRAPOLATION",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("x_error_px", type=float)
    parser.add_argument("y_error_px", type=float)
    args = parser.parse_args()
    result = evaluate((args.x_error_px, args.y_error_px))
    print(json.dumps(result, indent=2))
    return 0 if result["correctable_inside_cleared_envelope"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
