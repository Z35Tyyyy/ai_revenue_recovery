"""India compliance guardrails — RBI e-mandate / UPI Autopay / TRAI rules."""

from datetime import datetime, timezone

from recovery.compliance import check_action
from recovery.domain.models import ActionType, PaymentMethod

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def test_upi_retry_shifted_for_24h_pre_debit_notice():
    d = check_action(ActionType.RETRY_OPTIMAL, PaymentMethod.UPI_AUTOPAY, 49900, NOW, NOW)
    assert d.allowed
    # must be at least 24h out
    assert (d.adjusted_at - NOW).total_seconds() >= 24 * 3600 - 1
    assert any("pre-debit" in n for n in d.notes)


def test_afa_cap_blocks_silent_large_debit():
    d = check_action(ActionType.RETRY_NOW, PaymentMethod.UPI_AUTOPAY, 20_000_00, NOW, NOW)
    assert not d.allowed
    assert d.requires_afa


def test_card_retry_not_subject_to_mandate_rules():
    d = check_action(ActionType.RETRY_NOW, PaymentMethod.CARD, 999900, NOW, NOW)
    assert d.allowed and not d.requires_afa


def test_message_blocked_without_consent():
    d = check_action(ActionType.DUNNING_NUDGE, PaymentMethod.CARD, 49900, NOW, NOW, consent=False)
    assert not d.allowed


def test_message_frequency_cap():
    d = check_action(
        ActionType.DUNNING_NUDGE, PaymentMethod.CARD, 49900, NOW, NOW, messages_sent_this_week=3
    )
    assert not d.allowed


def test_message_shifted_out_of_quiet_hours():
    late = NOW.replace(hour=23)
    d = check_action(ActionType.DUNNING_NUDGE, PaymentMethod.CARD, 49900, late, late)
    assert d.allowed
    assert 8 <= d.adjusted_at.hour < 21
