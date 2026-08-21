from recovery.domain.models import RecoverabilityClass, format_inr
from recovery.domain.taxonomy import classify_reason, reason_codes


def test_classify_known_and_unknown():
    r = classify_reason("insufficient_funds")
    assert r.recoverability is RecoverabilityClass.INSUFFICIENT_FUNDS
    assert r.salary_sensitive is True
    assert r.retry_helps is True

    hard = classify_reason("stolen_or_lost_card")
    assert hard.recoverability is RecoverabilityClass.HARD_DECLINE
    assert hard.retry_helps is False

    # unknown / empty codes degrade gracefully
    assert classify_reason("totally_made_up").recoverability is RecoverabilityClass.UNKNOWN
    assert classify_reason(None).recoverability is RecoverabilityClass.UNKNOWN


def test_taxonomy_probs_are_valid():
    for code in reason_codes():
        r = classify_reason(code)
        assert 0.0 <= r.prior_recover_prob <= 1.0
        assert r.recommended_actions  # every reason recommends at least one action


def test_format_inr_indian_grouping():
    assert format_inr(149900) == "₹1,499"
    assert format_inr(4999900) == "₹49,999"
    assert format_inr(100000000) == "₹10,00,000"  # 10 lakh grouping
    assert format_inr(50) == "₹0.50"
