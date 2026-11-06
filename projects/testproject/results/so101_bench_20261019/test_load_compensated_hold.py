#!/usr/bin/env python3

import numpy as np
import pytest
from load_compensated_hold import (
    CompensationLimitError,
    LoadCompensationState,
    compensated_arm_command,
)


def test_bias_is_retained_across_alignment_and_capture_phases():
    target = np.zeros(5, dtype=np.float32)
    measured = np.array([0.0, 0.0, -1.0, 0.0, 0.0], dtype=np.float32)
    bias = np.zeros(5, dtype=np.float32)

    for _ in range(20):
        _, bias, _ = compensated_arm_command(target, measured, bias)
    assert bias[2] == pytest.approx(1.0)

    command, retained_bias, _ = compensated_arm_command(target, measured, bias)
    assert retained_bias[2] == pytest.approx(1.05)
    assert command[2] == pytest.approx(1.05)


def test_compensation_limit_refuses_before_command_is_returned():
    with pytest.raises(CompensationLimitError):
        compensated_arm_command(
            np.zeros(5),
            np.full(5, -1.0),
            np.full(5, 4.99),
        )


def test_state_retains_bias_across_separate_capture_commands():
    state = LoadCompensationState()
    target = np.zeros(5, dtype=np.float32)
    measured = np.array([0.0, 0.0, -1.0, 0.0, 0.0], dtype=np.float32)

    for _ in range(20):
        state.command(target, measured)
    first_capture_bias = state.bias.copy()
    state.command(target, measured)

    assert first_capture_bias[2] == pytest.approx(1.0)
    assert state.bias[2] == pytest.approx(1.05)


def test_invalid_joint_vector_is_rejected():
    with pytest.raises(ValueError):
        compensated_arm_command(np.zeros(4), np.zeros(5), np.zeros(5))


def test_encoder_scale_error_inside_deadband_does_not_wind_up_bias():
    target = np.zeros(5, dtype=np.float32)
    measured = np.full(5, 0.1, dtype=np.float32)
    bias = np.array([0.0, 0.0, -4.6, 0.0, 0.0], dtype=np.float32)

    for _ in range(100):
        _, bias, _ = compensated_arm_command(target, measured, bias)

    assert bias.tolist() == pytest.approx([0.0, 0.0, -4.6, 0.0, 0.0])
