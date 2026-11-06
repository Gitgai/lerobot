from bounded_wrist_correction import evaluate


def test_zero_error_is_correctable():
    result = evaluate((0.0, 0.0))
    assert result["correctable_inside_cleared_envelope"]
    assert result["decision"] == "ALLOW_LOCAL_REFINEMENT"


def test_secured_orange_error_refuses_extrapolation():
    result = evaluate((-22.53, -17.57))
    assert not result["correctable_inside_cleared_envelope"]
    assert result["decision"] == "REFUSE_LOCAL_EXTRAPOLATION"
    assert result["unbounded_zero_error_solution"] == {
        "pan_deg": -3.07,
        "radial_mm": 3.629,
        "inside_cleared_envelope": False,
    }
    assert result["best_cleared_solution"]["predicted_residual_px"] == [-13.06, -8.82]


def test_small_error_can_enter_gate():
    result = evaluate((-6.0, -3.0))
    assert result["correctable_inside_cleared_envelope"]
