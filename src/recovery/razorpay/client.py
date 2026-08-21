"""Razorpay test-mode gateway wrapper, with a faithful mock fallback.

When ``RAZORPAY_KEY_ID`` / ``RAZORPAY_KEY_SECRET`` are set, this talks to the real
Razorpay test-mode API (creating actual, payable test Payment Links). When they're
absent, :class:`MockGateway` returns deterministic look-alikes so the demo and the
API run anywhere. The interface is identical, so the engine never knows which is live.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Protocol

from recovery.config import Settings, get_settings
from recovery.domain.models import Customer, RecoveryCase


@dataclass
class PaymentLink:
    id: str
    short_url: str
    amount_paise: int
    status: str = "created"
    is_mock: bool = True
    notes: dict = field(default_factory=dict)


class Gateway(Protocol):
    @property
    def live(self) -> bool: ...

    def create_customer(self, customer: Customer) -> str: ...

    def create_payment_link(
        self, case: RecoveryCase, description: str
    ) -> PaymentLink: ...


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
                "notify": {"sms": True, "email": True},
                "reminder_enable": True,
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


def get_gateway(settings: Settings | None = None) -> Gateway:
    settings = settings or get_settings()
    if settings.razorpay_enabled:
        try:
            return RazorpayGateway(settings)
        except Exception:
            # SDK missing or auth malformed — degrade to mock rather than crash.
            return MockGateway()
    return MockGateway()
