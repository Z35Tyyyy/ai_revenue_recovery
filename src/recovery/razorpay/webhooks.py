"""Razorpay webhook handling: signature verification + payload parsing.

Signature verification is the non-negotiable security step for any real payments
integration, so we implement it explicitly (HMAC-SHA256 over the raw body, constant-
time compare) rather than hand-waving it. Parsing maps a ``payment.failed`` event
into our :class:`FailureEvent`, normalising Razorpay's error vocabulary onto the
recoverability taxonomy.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

from recovery.domain.models import FailureEvent, PaymentMethod
from recovery.domain.taxonomy import FAILURE_REASONS

# Normalise Razorpay error reasons/codes onto our taxonomy vocabulary.
_REASON_ALIASES = {
    "payment_failed": "do_not_honour",
    "gateway_error": "gateway_technical_error",
    "server_error": "gateway_technical_error",
    "issuer_down": "issuer_unavailable",
    "bank_error": "issuer_unavailable",
    "expired_card": "card_expired",
    "card_declined": "do_not_honour",
    "incorrect_otp": "authentication_failed",
    "invalid_otp": "authentication_failed",
    "payment_frequency_limit_exceeded": "payment_frequency_exceeded",
    "amount_limit_exceeded": "transaction_limit_exceeded",
    "mandate_cancelled": "mandate_revoked",
    "lost_or_stolen_card": "stolen_or_lost_card",
    "account_frozen": "payer_account_frozen",
}
_METHOD_MAP = {
    "card": PaymentMethod.CARD,
    "upi": PaymentMethod.UPI_AUTOPAY,
    "netbanking": PaymentMethod.NETBANKING,
    "wallet": PaymentMethod.WALLET,
    "emandate": PaymentMethod.EMANDATE,
    "nach": PaymentMethod.EMANDATE,
}


def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Constant-time verify the ``X-Razorpay-Signature`` header against the raw body."""
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _normalise_reason(entity: dict) -> str:
    raw = (entity.get("error_reason") or entity.get("error_code") or "").strip().lower()
    if raw in FAILURE_REASONS:
        return raw
    if raw in _REASON_ALIASES:
        return _REASON_ALIASES[raw]
    # try the human description as a last resort
    desc = (entity.get("error_description") or "").lower()
    for code in FAILURE_REASONS:
        if code.replace("_", " ") in desc:
            return code
    return "unknown"


# Events that mean "a recurring charge failed / needs recovery". `subscription.pending`
# (retry in progress) and `subscription.halted` (retries exhausted) are the real
# recovery trigger surface for recurring billing — not just raw `payment.failed`.
_FAILURE_EVENTS = {"payment.failed", "subscription.pending", "subscription.halted"}
# Events that mean "the customer paid" — used to close the recovery loop.
_RECOVERY_EVENTS = {"payment.captured", "subscription.charged"}


def is_recovery_confirmation(event: dict) -> str | None:
    """Return the recovered payment/subscription id for a success event, else None."""
    ev = event.get("event")
    if ev not in _RECOVERY_EVENTS:
        return None
    payload = event.get("payload", {})
    entity = payload.get("payment", {}).get("entity", {}) or payload.get(
        "subscription", {}
    ).get("entity", {})
    return entity.get("id")


def parse_failure_event(event: dict) -> FailureEvent | None:
    """Turn a Razorpay recovery-trigger webhook into a :class:`FailureEvent`.

    Handles ``payment.failed`` and the subscription lifecycle events
    ``subscription.pending`` / ``subscription.halted``. Returns ``None`` otherwise.
    """
    if event.get("event") not in _FAILURE_EVENTS:
        return None
    payload = event.get("payload", {})
    entity = payload.get("payment", {}).get("entity", {})
    sub_entity = payload.get("subscription", {}).get("entity", {})
    if not entity and not sub_entity:
        return None
    # Prefer the failed payment's details; fall back to the subscription entity.
    notes = entity.get("notes") or sub_entity.get("notes") or {}
    created = entity.get("created_at")
    occurred = (
        datetime.fromtimestamp(created, tz=timezone.utc)
        if isinstance(created, (int, float))
        else datetime.now(timezone.utc)
    )
    method = _METHOD_MAP.get((entity.get("method") or "card").lower(), PaymentMethod.CARD)

    return FailureEvent(
        id=f"fail_{entity.get('id', 'unknown')}",
        subscription_id=notes.get("subscription_id", f"sub_{notes.get('case_id', 'wh')}"),
        customer_id=notes.get("customer_id", entity.get("customer_id", "cust_webhook")),
        occurred_at=occurred,
        amount_paise=int(entity.get("amount", 0)),
        method=method,
        reason_code=_normalise_reason(entity),
        attempt_number=int(notes.get("attempt_number", 1)),
        razorpay_payment_id=entity.get("id"),
        razorpay_order_id=entity.get("order_id"),
    )
