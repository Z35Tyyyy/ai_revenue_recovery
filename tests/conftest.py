"""Shared fixtures: a small trained-model bundle reused across engine/eval tests."""

from __future__ import annotations

import pytest

from recovery.ml.train import train_recovery_model, train_timing_model
from recovery.simulation.generator import generate_population
from recovery.simulation.history import build_training_logs


@pytest.fixture(autouse=True)
def _isolate_credentials(monkeypatch):
    """Run every test hermetically — ignore any developer's local .env and clear
    credentials — so tests are deterministic (mock gateway + template dunning,
    fail-closed webhooks) and never touch the live Razorpay/LLM services."""
    from recovery.config import Settings, get_settings

    # Ignore the repo .env file entirely; tests control settings via env vars only.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    # Ephemeral in-memory store so tests never touch (or persist to) a real DB file.
    monkeypatch.setenv("RECOVERY_DB", ":memory:")
    for var in (
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
        "RAZORPAY_WEBHOOK_SECRET",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "OPENAI_API_KEY",
        "RECOVERY_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def trained_bundle():
    pop = generate_population(n_customers=600, n_failures=2000, seed=7)
    timing, cases = build_training_logs(pop, seed=7)
    recovery_model, _ = train_recovery_model(cases, seed=7)
    timing_model, _ = train_timing_model(timing, seed=7)
    return recovery_model, timing_model


@pytest.fixture(scope="session")
def holdout():
    return generate_population(n_customers=800, n_failures=2000, seed=9999)
