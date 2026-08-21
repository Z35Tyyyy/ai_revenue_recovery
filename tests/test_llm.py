"""LLM provider selection + template fallback (no network)."""

from datetime import datetime, timezone

from recovery.config import Settings
from recovery.domain.models import (
    Channel,
    Customer,
    FailureEvent,
    Language,
    PaymentMethod,
    RecoveryCase,
    Subscription,
)
from recovery.llm.dunning import DunningGenerator


def _case(reason="card_expired", language=Language.HI):
    cust = Customer(id="c1", name="Asha Menon", language=language,
                    preferred_channel=Channel.WHATSAPP, tenure_months=12)
    sub = Subscription(id="s1", customer_id="c1", plan_name="Pro", amount_paise=49900)
    fail = FailureEvent(
        id="f1", subscription_id="s1", customer_id="c1",
        occurred_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        amount_paise=49900, method=PaymentMethod.CARD, reason_code=reason,
    )
    return RecoveryCase(id="case_f1", failure=fail, customer=cust, subscription=sub)


def test_provider_selection_groq(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key")
    monkeypatch.delenv("RECOVERY_LLM_MODEL", raising=False)
    s = Settings()
    assert s.llm_enabled is True
    assert s.active_llm_key == "gsk_test_key"
    assert "llama" in s.resolved_llm_model  # groq's sensible default


def test_provider_without_key_is_disabled(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    s = Settings()
    assert s.llm_enabled is False
    assert s.resolved_llm_model == "claude-opus-5"


def test_force_templates_never_calls_llm():
    gen = DunningGenerator(force_templates=True)
    assert gen.uses_llm is False
    msg = gen.generate(_case(), Channel.WHATSAPP, Language.HI)
    assert msg.authored_by == "template"
    assert msg.quality == 0.85
    assert "₹" in msg.text  # a real localised message was produced


def test_templates_are_multilingual():
    gen = DunningGenerator(force_templates=True)
    hinglish = gen.generate(_case(language=Language.HINGLISH), Channel.WHATSAPP, Language.HINGLISH)
    assert "pending" in hinglish.text.lower() or "plan" in hinglish.text.lower()
    hindi = gen.generate(_case(language=Language.HI), Channel.WHATSAPP, Language.HI)
    assert any("ऀ" <= ch <= "ॿ" for ch in hindi.text)  # Devanagari present
