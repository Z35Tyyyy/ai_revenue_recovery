"""Razorpay-grounded failure-reason taxonomy.

Every recurring charge that fails comes back with an error ``reason`` code. Those
raw codes are the single most predictive signal for recovery, but they're only
useful once mapped onto *what action can actually fix them*. This module encodes
that mapping as domain knowledge:

* ``recoverability`` — the class that decides which actions even make sense.
* ``prior_recover_prob`` — a hand-set expert prior (what a good rules engine would
  believe). The ML model learns the *real* function, including interactions the
  prior can't express (salary-cycle timing, customer engagement, attempt number).
* ``recommended_actions`` — ordered fallback for the policy / cold-start.
* ``retry_helps`` — whether a bare retry (no customer action) can ever succeed.

Codes follow Razorpay's payment-failure vocabulary; unknown codes degrade to a
conservative ``UNKNOWN`` entry rather than crashing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from recovery.domain.models import ActionType, RecoverabilityClass

__all__ = [
    "FailureReason",
    "FAILURE_REASONS",
    "RecoverabilityClass",
    "classify_reason",
    "reason_codes",
    "UNKNOWN_REASON",
]


@dataclass(frozen=True)
class FailureReason:
    code: str
    description: str
    recoverability: RecoverabilityClass
    prior_recover_prob: float
    retry_helps: bool
    recommended_actions: tuple[ActionType, ...] = field(default_factory=tuple)
    # Does timing the retry to salary day materially help? (India-native signal)
    salary_sensitive: bool = False


def _r(*a, **k) -> FailureReason:  # tiny constructor alias for a dense table
    return FailureReason(*a, **k)


# Ordered roughly by how often they show up on recurring debits in India.
_REASONS: list[FailureReason] = [
    _r(
        "insufficient_funds",
        "Customer's account/card lacked balance on debit day.",
        RecoverabilityClass.INSUFFICIENT_FUNDS,
        prior_recover_prob=0.62,
        retry_helps=True,
        recommended_actions=(ActionType.RETRY_OPTIMAL, ActionType.DUNNING_NUDGE),
        salary_sensitive=True,
    ),
    _r(
        "do_not_honour",
        "Issuer soft-declined without a specific reason (very common, often temporary).",
        RecoverabilityClass.SOFT_DECLINE,
        prior_recover_prob=0.48,
        retry_helps=True,
        recommended_actions=(ActionType.RETRY_OPTIMAL, ActionType.DUNNING_NUDGE),
        salary_sensitive=True,
    ),
    _r(
        "issuer_unavailable",
        "Issuing bank was temporarily unreachable / in downtime.",
        RecoverabilityClass.TRANSIENT,
        prior_recover_prob=0.78,
        retry_helps=True,
        recommended_actions=(ActionType.RETRY_NOW, ActionType.RETRY_OPTIMAL),
    ),
    _r(
        "gateway_technical_error",
        "Transient technical error at the network/gateway.",
        RecoverabilityClass.TRANSIENT,
        prior_recover_prob=0.80,
        retry_helps=True,
        recommended_actions=(ActionType.RETRY_NOW,),
    ),
    _r(
        "payment_frequency_exceeded",
        "Too many attempts on the instrument in a window; back off then retry.",
        RecoverabilityClass.SOFT_DECLINE,
        prior_recover_prob=0.55,
        retry_helps=True,
        recommended_actions=(ActionType.RETRY_OPTIMAL,),
    ),
    _r(
        "transaction_limit_exceeded",
        "Per-transaction or daily limit hit; retry later or split.",
        RecoverabilityClass.SOFT_DECLINE,
        prior_recover_prob=0.5,
        retry_helps=True,
        recommended_actions=(ActionType.RETRY_OPTIMAL, ActionType.DUNNING_NUDGE),
    ),
    _r(
        "card_expired",
        "Card on file has expired — retry is futile until the customer updates it.",
        RecoverabilityClass.NEEDS_CARD_UPDATE,
        prior_recover_prob=0.34,
        retry_helps=False,
        recommended_actions=(ActionType.REQUEST_CARD_UPDATE, ActionType.SWITCH_METHOD),
    ),
    _r(
        "card_disabled",
        "Card temporarily disabled for online/recurring use; customer must re-enable.",
        RecoverabilityClass.NEEDS_CARD_UPDATE,
        prior_recover_prob=0.3,
        retry_helps=False,
        recommended_actions=(ActionType.REQUEST_CARD_UPDATE, ActionType.SWITCH_METHOD),
    ),
    _r(
        "authentication_failed",
        "Additional-factor / OTP authentication failed on the debit.",
        RecoverabilityClass.NEEDS_REAUTH,
        prior_recover_prob=0.42,
        retry_helps=True,
        recommended_actions=(ActionType.DUNNING_NUDGE, ActionType.RETRY_OPTIMAL),
    ),
    _r(
        "mandate_paused",
        "UPI-autopay / e-mandate paused by the customer or bank.",
        RecoverabilityClass.NEEDS_REAUTH,
        prior_recover_prob=0.38,
        retry_helps=False,
        recommended_actions=(ActionType.DUNNING_NUDGE, ActionType.SWITCH_METHOD),
    ),
    _r(
        "mandate_revoked",
        "Mandate cancelled — needs a fresh authorisation to charge again.",
        RecoverabilityClass.NEEDS_REAUTH,
        prior_recover_prob=0.22,
        retry_helps=False,
        recommended_actions=(ActionType.SWITCH_METHOD, ActionType.OFFER_GRACE),
    ),
    _r(
        "international_transaction_not_allowed",
        "Instrument blocks recurring/international charges.",
        RecoverabilityClass.NEEDS_CARD_UPDATE,
        prior_recover_prob=0.28,
        retry_helps=False,
        recommended_actions=(ActionType.SWITCH_METHOD,),
    ),
    _r(
        "payer_account_frozen",
        "Customer's account is frozen/closed.",
        RecoverabilityClass.HARD_DECLINE,
        prior_recover_prob=0.08,
        retry_helps=False,
        recommended_actions=(ActionType.OFFER_GRACE, ActionType.GIVE_UP),
    ),
    _r(
        "stolen_or_lost_card",
        "Card reported stolen/lost — will not recover on this instrument.",
        RecoverabilityClass.HARD_DECLINE,
        prior_recover_prob=0.05,
        retry_helps=False,
        recommended_actions=(ActionType.SWITCH_METHOD, ActionType.GIVE_UP),
    ),
    _r(
        "invalid_card",
        "Card number/details invalid — unrecoverable without a new instrument.",
        RecoverabilityClass.HARD_DECLINE,
        prior_recover_prob=0.06,
        retry_helps=False,
        recommended_actions=(ActionType.SWITCH_METHOD, ActionType.GIVE_UP),
    ),
]

FAILURE_REASONS: dict[str, FailureReason] = {r.code: r for r in _REASONS}

UNKNOWN_REASON = _r(
    "unknown",
    "Unrecognised failure reason — treated conservatively as a soft decline.",
    RecoverabilityClass.UNKNOWN,
    prior_recover_prob=0.35,
    retry_helps=True,
    recommended_actions=(ActionType.RETRY_OPTIMAL, ActionType.DUNNING_NUDGE),
)


def classify_reason(code: str | None) -> FailureReason:
    """Map a raw Razorpay reason code to its :class:`FailureReason` (never raises)."""
    if not code:
        return UNKNOWN_REASON
    return FAILURE_REASONS.get(code.strip().lower(), UNKNOWN_REASON)


def reason_codes() -> list[str]:
    return list(FAILURE_REASONS.keys())
