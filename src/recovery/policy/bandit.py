"""A contextual multi-armed bandit for action selection.

Context = the failure's recoverability class. Arms = the recovery action types.
Each (context, arm) keeps a Beta(α, β) posterior over "does this action recover
this kind of failure?". Thompson sampling draws from those posteriors so the
engine keeps exploring while exploiting what works — and, crucially, *corrects the
model's EV beliefs online*: if nudging ``mandate_revoked`` cases actually beats
retrying them, the posterior learns it from outcomes, no retraining required.

Deterministic given a seed, so eval runs reproduce exactly.
"""

from __future__ import annotations

import numpy as np

from recovery.domain.models import ActionType, RecoverabilityClass


class ContextualBandit:
    def __init__(self, seed: int = 7, prior_strength: float = 1.0) -> None:
        self._rng = np.random.default_rng(seed)
        self._prior = prior_strength
        # (context, arm) -> [alpha, beta]
        self._ab: dict[tuple[str, str], list[float]] = {}

    def _key(self, context: RecoverabilityClass, arm: ActionType) -> tuple[str, str]:
        return (context.value, arm.value)

    def _params(self, context: RecoverabilityClass, arm: ActionType) -> list[float]:
        return self._ab.setdefault(self._key(context, arm), [self._prior, self._prior])

    def sample(self, context: RecoverabilityClass, arm: ActionType) -> float:
        a, b = self._params(context, arm)
        return float(self._rng.beta(a, b))

    def mean(self, context: RecoverabilityClass, arm: ActionType) -> float:
        a, b = self._params(context, arm)
        return a / (a + b)

    def update(self, context: RecoverabilityClass, arm: ActionType, reward: bool) -> None:
        p = self._params(context, arm)
        if reward:
            p[0] += 1.0
        else:
            p[1] += 1.0

    def snapshot(self) -> dict[str, dict[str, float]]:
        """Learned success rate per (context, arm) — only arms actually tried.

        Untried arms sit at their 0.5 prior and would misleadingly read as "best",
        so we exclude them; what remains is what the bandit genuinely learned.
        """
        out: dict[str, dict[str, float]] = {}
        for (ctx, arm), (a, b) in sorted(self._ab.items()):
            observations = (a - self._prior) + (b - self._prior)
            if observations <= 0:
                continue
            out.setdefault(ctx, {})[arm] = round(a / (a + b), 3)
        return out
