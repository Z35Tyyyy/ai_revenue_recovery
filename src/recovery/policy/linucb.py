"""LinUCB — a *contextual* bandit over the full feature vector.

The default policy's Thompson bandit conditions on one categorical (the failure
class). This conditions the exploration/exploitation on the whole observable
context — amount, tenure, salary proximity, instrument, class — so the policy can
learn, e.g., "nudge high-tenure insufficient-funds customers, retry the rest".

Disjoint LinUCB (Li et al., WWW 2010): per arm keep A = I + Σ xxᵀ and b = Σ r·x;
score = θ·x + α·√(xᵀA⁻¹x) (mean + optimism bonus); pick the argmax.

Exposed as the upgrade path for the engine's online correction; the batch eval keeps
the simpler Thompson bandit for reproducibility.
"""

from __future__ import annotations

import math

import numpy as np

from recovery.domain.models import RecoverabilityClass, RecoveryCase
from recovery.domain.taxonomy import classify_reason
from recovery.ml.features import days_since_salary

_CLASSES = list(RecoverabilityClass)


def context_vector(case: RecoveryCase) -> np.ndarray:
    """Fixed-dimension numeric context from OBSERVABLE features only (no latents)."""
    f, c = case.failure, case.customer
    reason = classify_reason(f.reason_code)
    dsl = days_since_salary(f.occurred_at.day, c.salary_day)
    base = [
        1.0,                                             # bias
        float(reason.prior_recover_prob),
        1.0 if reason.retry_helps else 0.0,
        1.0 if reason.salary_sensitive else 0.0,
        math.log1p(f.amount_paise / 100.0) / 12.0,       # ~[0,1]
        min(c.tenure_months, 60) / 60.0,
        1.0 if dsl <= 2 else 0.0,                         # near payday
        float(f.attempt_number) / 5.0,
    ]
    onehot = [1.0 if reason.recoverability is k else 0.0 for k in _CLASSES]
    return np.array(base + onehot, dtype=float)


CONTEXT_DIM = 8 + len(_CLASSES)


class LinUCBBandit:
    def __init__(self, arms: list[str], dim: int = CONTEXT_DIM, alpha: float = 0.6) -> None:
        self.arms = list(arms)
        self.dim = dim
        self.alpha = alpha
        self.A = {a: np.identity(dim) for a in self.arms}
        self.b = {a: np.zeros(dim) for a in self.arms}

    def scores(self, x: np.ndarray) -> dict[str, float]:
        out: dict[str, float] = {}
        for a in self.arms:
            a_inv = np.linalg.inv(self.A[a])
            theta = a_inv @ self.b[a]
            mean = float(theta @ x)
            bonus = self.alpha * math.sqrt(max(0.0, float(x @ a_inv @ x)))
            out[a] = mean + bonus
        return out

    def select(self, x: np.ndarray) -> str:
        scores = self.scores(x)
        return max(scores, key=scores.get)

    def update(self, arm: str, x: np.ndarray, reward: float) -> None:
        self.A[arm] += np.outer(x, x)
        self.b[arm] += reward * x
