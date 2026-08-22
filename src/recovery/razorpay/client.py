"""Razorpay test-mode gateway wrapper, with a faithful mock fallback.

When ``RAZORPAY_KEY_ID`` / ``RAZORPAY_KEY_SECRET`` are set, this talks to the real
Razorpay test-mode API (creating actual, payable test Payment Links). When they're
absent, :class:`MockGateway` returns deterministic look-alikes so the demo and the
API run anywhere. The interface is identical, so the engine never knows which is live.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Protocol

from recovery.config import Settings, get_settings
from recovery.domain.models import Customer, RecoveryCase

logger = logging.getLogger("recovery.razorpay")


@dataclass
class PaymentLink:
    id: str
    short_url: str
    amount_paise: int
    status: str = "created"
    is_mock: bool = True
    notes: dict = field(default_factory=dict)


@dataclass
class Subscription:
    id: str
    short_url: str
    status: str = "created"
    is_mock: bool = True


class Gateway(Protocol):
    @property
    def live(self) -> bool: ...

    def create_customer(self, customer: Customer) -> str: ...

    def create_payment_link(
        self, case: RecoveryCase, description: str
    ) -> PaymentLink: ...

    def create_subscription(
        self, customer: Customer, amount_paise: int, plan_name: str
    ) -> Subscription: ...

    def fetch_payment_link_status(self, link_id: str) -> str: ...


class MockGateway:
    """Deterministic, offline stand-in for the Razorpay API."""

    live = False

    def _hash(self, *parts: object) -> str:
        return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:14]

    def create_customer(self, customer: Customer) -> str:
        return f"cust_MOCK{self._hash(customer.id)}"

    def create_payment_link(self, case: RecoveryCase, description: str) -> PaymentLink:
        h = self._hash(case.id, case.failure.amount_paise)
        return PaymentLink(
            id=f"plink_MOCK{h}",
            short_url=f"https://rzp.io/i/mock{h[:8]}",
            amount_paise=case.failure.amount_paise,
            status="created",
            is_mock=True,
            notes={"case_id": case.id, "reason": case.failure.reason_code},
        )

    def create_subscription(
        self, customer: Customer, amount_paise: int, plan_name: str
    ) -> Subscription:
        h = self._hash(customer.id, amount_paise, plan_name)
        return Subscription(id=f"sub_MOCK{h}", short_url=f"https://rzp.io/i/submock{h[:8]}")

    def fetch_payment_link_status(self, link_id: str) -> str:
        return "paid"  # mock link is treated as paid so the demo loop closes


class RazorpayGateway:
    """Real Razorpay test-mode gateway (lazy SDK import; never used without keys)."""

    live = True

    def __init__(self, settings: Settings) -> None:
        import razorpay  # noqa: PLC0415 (lazy: keep razorpay optional)

        self._client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )

    def create_customer(self, customer: Customer) -> str:
        resp = self._client.customer.create(
            {
                "name": customer.name or "Recovery Customer",
                "email": customer.email or "customer@example.in",
                "contact": customer.phone or "+919000000000",
                "fail_existing": "0",
            }
        )
        return resp["id"]

    def create_payment_link(self, case: RecoveryCase, description: str) -> PaymentLink:
        cust = case.customer
        # Only notify on channels where we actually have a real contact — never
        # blast SMS/email to placeholder recipients.
        has_email = bool(cust.email)
        has_phone = bool(cust.phone)
        resp = self._client.payment_link.create(
            {
                "amount": case.failure.amount_paise,
                "currency": "INR",
                "accept_partial": False,
                "description": description[:2048],
                "customer": {
                    "name": cust.name or "Recovery Customer",
                    "email": cust.email or "customer@example.in",
                    "contact": cust.phone or "+919000000000",
                },
                "notify": {"sms": has_phone, "email": has_email},
                "reminder_enable": bool(has_email or has_phone),
                "notes": {"case_id": case.id, "reason": case.failure.reason_code},
            }
        )
        return PaymentLink(
            id=resp["id"],
            short_url=resp["short_url"],
            amount_paise=resp["amount"],
            status=resp.get("status", "created"),
            is_mock=False,
            notes=resp.get("notes", {}),
        )

    def create_subscription(
        self, customer: Customer, amount_paise: int, plan_name: str
    ) -> Subscription:
        # Create a plan then a subscription — the real recurring-billing surface a
        # recovery agent monitors via subscription.pending / halted webhooks.
        plan = self._client.plan.create(
            {
                "period": "monthly",
                "interval": 1,
                "item": {"name": plan_name[:64], "amount": amount_paise, "currency": "INR"},
            }
        )
        resp = self._client.subscription.create(
            {
                "plan_id": plan["id"],
                "total_count": 12,
                "quantity": 1,
                "customer_notify": 1,
                "notes": {"customer_id": customer.id},
            }
        )
        return Subscription(
            id=resp["id"],
            short_url=resp.get("short_url", ""),
            status=resp.get("status", "created"),
            is_mock=False,
        )

    def fetch_payment_link_status(self, link_id: str) -> str:
        """Poll Razorpay for a link's status ('created' | 'paid' | 'cancelled' | …).

        This is how the loop closes with real Razorpay data WITHOUT an inbound webhook:
        the customer pays the link, we poll, and a 'paid' status confirms the recovery.
        """
        resp = self._client.payment_link.fetch(link_id)
        return resp.get("status", "unknown")


def get_gateway(settings: Settings | None = None) -> Gateway:
    settings = settings or get_settings()
    if settings.razorpay_enabled:
        try:
            return RazorpayGateway(settings)
        except Exception:
            # SDK missing or auth malformed — degrade to mock rather than crash.
            logger.warning(
                "Razorpay keys set but gateway init failed — using mock gateway", exc_info=True
            )
            return MockGateway()
    return MockGateway()
