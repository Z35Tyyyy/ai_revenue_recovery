import hashlib
import hmac

from recovery.domain.models import PaymentMethod
from recovery.razorpay.client import MockGateway
from recovery.razorpay.webhooks import parse_failure_event, verify_webhook_signature


def test_signature_verification():
    body = b'{"event":"payment.failed","payload":{}}'
    secret = "whsec_test"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, sig, secret) is True
    assert verify_webhook_signature(body, sig, "wrong_secret") is False
    assert verify_webhook_signature(body, "", secret) is False


def test_parse_payment_failed_event():
    event = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_TEST123",
                    "order_id": "order_TEST123",
                    "amount": 49900,
                    "method": "upi",
                    "error_reason": "insufficient_funds",
                    "created_at": 1_770_000_000,
                    "notes": {
                        "customer_id": "cust_00042",
                        "subscription_id": "sub_00042",
                        "attempt_number": 2,
                    },
                }
            }
        },
    }
    fe = parse_failure_event(event)
    assert fe is not None
    assert fe.amount_paise == 49900
    assert fe.reason_code == "insufficient_funds"
    assert fe.method is PaymentMethod.UPI_AUTOPAY
    assert fe.attempt_number == 2
    assert fe.razorpay_payment_id == "pay_TEST123"


def test_parse_aliases_unknown_reason():
    event = {
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"amount": 100, "error_reason": "expired_card"}}},
    }
    fe = parse_failure_event(event)
    assert fe.reason_code == "card_expired"  # aliased onto the taxonomy


def test_non_failure_events_ignored():
    assert parse_failure_event({"event": "payment.captured", "payload": {}}) is None


def test_mock_gateway_is_deterministic():
    from datetime import datetime, timezone

    from recovery.domain.models import Customer, FailureEvent, RecoveryCase, Subscription

    cust = Customer(id="c1")
    sub = Subscription(id="s1", customer_id="c1", amount_paise=49900)
    fail = FailureEvent(
        id="f1", subscription_id="s1", customer_id="c1",
        occurred_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        amount_paise=49900, method=PaymentMethod.CARD, reason_code="insufficient_funds",
    )
    case = RecoveryCase(id="case_f1", failure=fail, customer=cust, subscription=sub)
    g = MockGateway()
    a = g.create_payment_link(case, "x")
    b = g.create_payment_link(case, "x")
    assert a.short_url == b.short_url and a.is_mock is True
