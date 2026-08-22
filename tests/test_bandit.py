"""Unit tests for the contextual bandit — the online policy correction that had
no direct coverage. Exercises the update rule, snapshot semantics, and seeded
reproducibility (the last matters because the eval relies on it)."""

from __future__ import annotations

from recovery.domain.models import ActionType, RecoverabilityClass
from recovery.policy.bandit import ContextualBandit

CTX = RecoverabilityClass.INSUFFICIENT_FUNDS
ARM = ActionType.RETRY_OPTIMAL


def test_update_moves_posterior_toward_outcomes():
    b = ContextualBandit(seed=1)
    base = b.mean(CTX, ARM)  # 0.5 prior
    for _ in range(20):
        b.update(CTX, ARM, reward=True)
    assert b.mean(CTX, ARM) > base
    for _ in range(60):
        b.update(CTX, ARM, reward=False)
    assert b.mean(CTX, ARM) < base  # now dominated by failures


def test_snapshot_excludes_untried_arms():
    b = ContextualBandit(seed=1)
    # Sampling alone must NOT register as an observation.
    _ = b.sample(CTX, ARM)
    assert b.snapshot() == {}
    b.update(CTX, ARM, reward=True)
    snap = b.snapshot()
    assert CTX.value in snap and ARM.value in snap[CTX.value]
    # Untried arm in the same context stays absent.
    assert ActionType.SWITCH_METHOD.value not in snap[CTX.value]


def test_seeded_reproducibility():
    a, b = ContextualBandit(seed=7), ContextualBandit(seed=7)
    draws_a = [a.sample(CTX, ARM) for _ in range(5)]
    draws_b = [b.sample(CTX, ARM) for _ in range(5)]
    assert draws_a == draws_b  # same seed → identical draw sequence
    draws_c = [ContextualBandit(seed=8).sample(CTX, ARM) for _ in range(5)]
    assert draws_c != draws_a  # different seed → different draws
