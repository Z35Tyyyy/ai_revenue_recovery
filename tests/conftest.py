"""Shared fixtures: a small trained-model bundle reused across engine/eval tests."""

from __future__ import annotations

import pytest

from recovery.ml.train import train_recovery_model, train_timing_model
from recovery.simulation.generator import generate_population
from recovery.simulation.history import build_training_logs


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
