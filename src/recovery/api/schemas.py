"""Request/response schemas for the API."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from recovery.domain.models import Channel, Language, PaymentMethod

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\-\s]{6,17}$")


class PlanRequest(BaseModel):
    """A failed recurring charge to diagnose and plan a recovery for."""

    reason_code: str = Field(default="insufficient_funds", max_length=64)
    amount_paise: int = Field(default=49900, ge=100, le=100_000_000)
    method: PaymentMethod = PaymentMethod.CARD
    plan_name: str = Field(default="Pro", max_length=80)
    attempt_number: int = Field(default=1, ge=1, le=20)
    # customer
    language: Language = Language.HINGLISH
    preferred_channel: Channel = Channel.WHATSAPP
    city: str = Field(default="Mumbai", max_length=60)
    tenure_months: int = Field(default=12, ge=0, le=600)
    salary_day: int = Field(default=1, ge=1, le=31)
    customer_name: str = Field(default="", max_length=80)
    customer_email: str = Field(default="", max_length=254)
    customer_phone: str = Field(default="", max_length=20)
    # Opt-in: creating a real link hits the live gateway and can notify the customer.
    create_payment_link: bool = False

    @field_validator("customer_email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        if v and not _EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v

    @field_validator("customer_phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        if v and not _PHONE_RE.match(v):
            raise ValueError("invalid phone number")
        return v
