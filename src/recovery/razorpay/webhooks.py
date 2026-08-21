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


def parse_failure_event(event: dict) -> FailureEvent | None:
    """Turn a Razorpay ``payment.failed`` webhook into a :class:`FailureEvent`.

    Returns ``None`` for events we don't act on.
    """
    if event.get("event") != "payment.failed":
        return None
    entity = (
        event.get("payload", {}).get("payment", {}).get("entity", {})
    )
    if not entity:
        return None

    notes = entity.get("notes") or {}
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
