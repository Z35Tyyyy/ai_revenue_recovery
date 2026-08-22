"""Off-policy evaluation: estimators recover the engine's true value from logged data."""

from recovery.eval.offpolicy import evaluate_offpolicy


def test_ope_estimators_track_onpolicy_value(trained_bundle, holdout):
    rm, tm = trained_bundle
    ope = evaluate_offpolicy(holdout, rm, tm, max_failures=1500)

    # The engine beats the random logging policy...
    assert ope.onpolicy_value > ope.logging_value + 0.05
    # ...and the off-policy estimators (from logged data alone) recover the true value.
    assert abs(ope.snips - ope.onpolicy_value) < 0.10
    assert abs(ope.dr - ope.onpolicy_value) < 0.10
    assert abs(ope.ips - ope.onpolicy_value) < 0.12
    # sanity: all estimates are valid probabilities
    for v in (ope.dm, ope.ips, ope.snips, ope.dr):
        assert 0.0 <= v <= 1.0
