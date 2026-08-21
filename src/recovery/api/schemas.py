"""Request/response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from recovery.domain.models import Channel, Language, PaymentMethod


class PlanRequest(BaseModel):
    """A failed recurring charge to diagnose and plan a recovery for."""

    reason_code: str = Field(default="insufficient_funds")
    amount_paise: int = Field(default=49900, ge=100)
    method: PaymentMethod = PaymentMethod.CARD
    plan_name: str = "Pro"
    attempt_number: int = Field(default=1, ge=1)
    # customer
    language: Language = Language.HINGLISH
    preferred_channel: Channel = Channel.WHATSAPP
    city: str = "Mumbai"
    tenure_months: int = Field(default=12, ge=0)
    salary_day: int = Field(default=1, ge=1, le=31)
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    create_payment_link: bool = True
