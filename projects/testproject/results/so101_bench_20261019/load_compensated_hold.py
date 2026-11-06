#!/usr/bin/env python3
"""Pure helpers for retaining SO-101 load compensation across control phases."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


class CompensationLimitError(RuntimeError):
    """Raised before a load-compensated command exceeds its allowed bias."""


@dataclass
class LoadCompensationState:
    """Retain learned motor-command bias across alignment and capture calls."""

    bias: np.ndarray = field(default_factory=lambda: np.zeros(5, dtype=np.float32))

    def replace(self, bias: np.ndarray) -> None:
        bias = np.asarray(bias, dtype=np.float32)
        if bias.shape != (5,):
            raise ValueError("bias must contain five joints")
        self.bias = bias.copy()

    def command(self, target_arm: np.ndarray, measured_arm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        command, self.bias, error = compensated_arm_command(target_arm, measured_arm, self.bias)
        return command, error


def compensated_arm_command(
    target_arm: np.ndarray,
    measured_arm: np.ndarray,
    bias: np.ndarray,
    *,
    step_deg: float = 0.05,
    deadband_deg: float = 0.15,
    max_bias_deg: float = 5.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the next command while preserving the caller-owned learned bias."""
    target_arm = np.asarray(target_arm, dtype=np.float32)
    measured_arm = np.asarray(measured_arm, dtype=np.float32)
    bias = np.asarray(bias, dtype=np.float32)
    if target_arm.shape != (5,) or measured_arm.shape != (5,) or bias.shape != (5,):
        raise ValueError("target_arm, measured_arm and bias must each contain five joints")
    error = target_arm - measured_arm
    correction_error = np.where(np.abs(error) > deadband_deg, error, 0.0)
    next_bias = bias + np.clip(correction_error, -step_deg, step_deg)
    if float(np.abs(next_bias).max()) > max_bias_deg:
        raise CompensationLimitError(f"pose-hold compensation exceeded {max_bias_deg:.1f} deg")
    return target_arm + next_bias, next_bias, error
