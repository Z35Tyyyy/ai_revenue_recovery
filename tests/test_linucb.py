"""LinUCB contextual bandit learns context-dependent arm selection."""

import numpy as np

from recovery.policy.linucb import LinUCBBandit

X_HI = np.array([1.0, 1.0])   # "feature present"
X_LO = np.array([1.0, 0.0])   # "feature absent"


def test_learns_context_dependent_best_arm():
    b = LinUCBBandit(arms=["a", "b"], dim=2, alpha=0.3)
    # Ground truth: arm "a" wins when the feature is present, "b" when absent.
    for _ in range(60):
        b.update("a", X_HI, 1.0)
        b.update("a", X_LO, 0.0)
        b.update("b", X_HI, 0.0)
        b.update("b", X_LO, 1.0)
    assert b.select(X_HI) == "a"
    assert b.select(X_LO) == "b"


def test_context_vector_is_observable_only_and_fixed_dim():
    from datetime import datetime, timezone

    from recovery.domain.models import (
        Customer,
        FailureEvent,
        PaymentMethod,
        RecoveryCase,
        Subscription,
    )
    from recovery.policy.linucb import CONTEXT_DIM, context_vector

    cust = Customer(id="c1", tenure_months=12, salary_day=1)
    sub = Subscription(id="s1", customer_id="c1", amount_paise=49900)
    fail = FailureEvent(
        id="f1", subscription_id="s1", customer_id="c1",
        occurred_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        amount_paise=49900, method=PaymentMethod.CARD, reason_code="insufficient_funds",
    )
    x = context_vector(RecoveryCase(id="case", failure=fail, customer=cust, subscription=sub))
    assert x.shape == (CONTEXT_DIM,)
    assert x[0] == 1.0  # bias term
