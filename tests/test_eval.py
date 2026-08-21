from recovery.eval.harness import evaluate


def test_engine_beats_all_baselines(trained_bundle, holdout):
    rm, tm = trained_bundle
    result = evaluate(holdout, rm, tm)
    p = result.policies

    # the value ladder must hold: engine > generic dunning > fixed retry > nothing
    assert p["no_action"].recovery_rate == 0.0
    assert p["fixed_retry"].recovery_rate > 0.2
    assert p["generic_dunning"].recovery_rate > p["fixed_retry"].recovery_rate
    assert p["engine"].recovery_rate > p["generic_dunning"].recovery_rate

    # a materially large, not fluke-sized, lift over the Razorpay-style default
    up = result.uplift_vs("fixed_retry", "engine")
    assert up["recovery_rate_abs"] > 0.08

    # engine should recover more while hammering the bank less
    assert p["engine"].retries < p["fixed_retry"].retries


def test_engine_is_efficient_on_hard_cases(trained_bundle, holdout):
    """On hard declines the engine should mostly give up, not spam messages."""
    rm, tm = trained_bundle
    result = evaluate(holdout, rm, tm)
    # hard declines exist in the holdout and the engine recovers almost none of them
    eng_by_class = result.policies["engine"].by_class_rate()
    assert eng_by_class.get("hard_decline", 0.0) < 0.15
