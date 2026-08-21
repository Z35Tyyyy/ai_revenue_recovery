"""The recovery *environment* — the hidden ground truth.

This is the part that makes the whole evaluation honest. Each failed payment gets
a set of **latent** parameters that a real merchant never observes directly: how
recoverable it truly is, when money will actually be in the account, how the
customer responds to a nudge. The environment turns a *(case, action, time)* into
a success/failure outcome by sampling from those latents.

Two consumers use it:

* the **history generator**, which runs a randomised logging policy through the
  environment to produce the observational dataset the ML models train on; and
* the **eval harness**, which runs each policy through the *same* dynamics on a
  fresh holdout, so measured uplift reflects real learned skill, not leakage.

Nothing in :mod:`recovery.ml` or :mod:`recovery.policy` may import from here — the
engine only ever sees observable features, never the latents.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from recovery.domain.models import (
    Channel,
    Customer,
    FailureEvent,
    Language,
    RecoverabilityClass,
    Subscription,
)
from recovery.domain.taxonomy import classify_reason

# Base per-class probability that a *well-timed, well-executed* recovery lands.
_CLASS_CEILING: dict[RecoverabilityClass, float] = {
    RecoverabilityClass.TRANSIENT: 0.92,
    RecoverabilityClass.INSUFFICIENT_FUNDS: 0.82,
    RecoverabilityClass.SOFT_DECLINE: 0.70,
    RecoverabilityClass.NEEDS_CARD_UPDATE: 0.55,
    RecoverabilityClass.NEEDS_REAUTH: 0.50,
    RecoverabilityClass.HARD_DECLINE: 0.06,
    RecoverabilityClass.UNKNOWN: 0.45,
}

# How much a *bare retry* (no customer action) can achieve, as a fraction of the
# ceiling. Classes that need the customer to do something can't be retried away.
_RETRY_REACH: dict[RecoverabilityClass, float] = {
    RecoverabilityClass.TRANSIENT: 1.0,
    RecoverabilityClass.INSUFFICIENT_FUNDS: 0.95,
    RecoverabilityClass.SOFT_DECLINE: 0.85,
    RecoverabilityClass.NEEDS_CARD_UPDATE: 0.08,
    RecoverabilityClass.NEEDS_REAUTH: 0.10,
    RecoverabilityClass.HARD_DECLINE: 0.02,
    RecoverabilityClass.UNKNOWN: 0.6,
}


def _seed_from(*parts: object) -> int:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:16], 16)


def _days_since_salary(at: datetime, salary_day: int) -> int:
    """Whole days since the customer was last paid (0 == payday), clamped to a month."""
    dom = at.day
    diff = dom - salary_day
    if diff < 0:
        diff += 30
    return diff


@dataclass
class LatentCase:
    """Hidden truth for a single failed payment."""

    failure_id: str
    recoverability: RecoverabilityClass
    ceiling: float                 # max achievable recovery prob for this case
    retry_reach: float             # fraction of ceiling reachable by bare retry
    optimal_hour: int              # hour-of-day that maximises success
    salary_sensitive: bool
    engagement: float              # customer responsiveness to nudges [0,1]
    salary_day: int
    # A per-case multiplier capturing idiosyncratic "this one is just sticky/easy".
    difficulty: float = 1.0

    def _timing_multiplier(self, at: datetime) -> float:
        """In [0,1]: how good this moment is for a retry."""
        # Hour-of-day effect: smooth bump around the case's optimal hour, plus the
        # real-world 00:xx auto-debit sweet spot.
        hour = at.hour
        circ = np.cos((hour - self.optimal_hour) / 24 * 2 * np.pi)
        hour_score = 0.6 + 0.4 * (circ * 0.5 + 0.5)
        midnight_bonus = 0.08 if hour in (0, 1) else 0.0

        # Funds-availability effect (only for salary-sensitive classes): highest just
        # after payday, decaying over the month.
        if self.salary_sensitive:
            dsl = _days_since_salary(at, self.salary_day)
            funds = 0.25 + 0.75 * float(np.exp(-dsl / 8.0))
        else:
            funds = 0.9  # non-fund failures barely care about the calendar
        return float(np.clip((hour_score + midnight_bonus) * funds, 0.0, 1.0))

    def retry_prob(self, at: datetime, attempt_number: int) -> float:
        """Probability a bare retry at ``at`` succeeds on attempt ``attempt_number``."""
        if self.recoverability is RecoverabilityClass.TRANSIENT:
            # Transient failures heal with wall-clock time regardless of hour.
            base = self.ceiling * self.retry_reach
        else:
            base = self.ceiling * self.retry_reach * self._timing_multiplier(at)
        fatigue = 0.82 ** max(0, attempt_number - 1)
        return float(np.clip(base * fatigue * self.difficulty, 0.0, 0.98))

    def dunning_prob(
        self,
        channel: Channel,
        language: Language,
        customer: Customer,
        message_quality: float,
    ) -> float:
        """Probability a dunning nudge converts the customer to pay via link."""
        # Dunning is how NEEDS_* classes actually get fixed; retry-heavy classes get
        # a smaller incremental lift from a nudge.
        if self.recoverability in (
            RecoverabilityClass.NEEDS_CARD_UPDATE,
            RecoverabilityClass.NEEDS_REAUTH,
        ):
            base = self.ceiling
        elif self.recoverability is RecoverabilityClass.HARD_DECLINE:
            base = self.ceiling
        else:
            base = self.ceiling * 0.55
        channel_match = 1.0 if channel == customer.preferred_channel else 0.72
        lang_match = 1.0 if language == customer.language else 0.78
        return float(
            np.clip(
                base * self.engagement * channel_match * lang_match * message_quality,
                0.0,
                0.97,
            )
        )


class RecoveryEnvironment:
    """Owns the latents and resolves actions into outcomes (seeded, reproducible)."""

    def __init__(
        self,
        customers: dict[str, Customer],
        subscriptions: dict[str, Subscription],
        seed: int = 7,
    ) -> None:
        self.customers = customers
        self.subscriptions = subscriptions
        self.seed = seed
        self.latents: dict[str, LatentCase] = {}
        self._fid_to_customer: dict[str, str] = {}

    # -- construction -------------------------------------------------------- #
    def build_latent(self, failure: FailureEvent) -> LatentCase:
        cust = self.customers[failure.customer_id]
        reason = classify_reason(failure.reason_code)
        rng = np.random.default_rng(_seed_from(self.seed, "latent", failure.id))

        ceiling = _CLASS_CEILING[reason.recoverability]
        # Loyal, high-engagement customers are genuinely more recoverable.
        ceiling *= 0.85 + 0.3 * cust.engagement
        ceiling = float(np.clip(ceiling + rng.normal(0, 0.03), 0.03, 0.97))

        # Optimal retry hour: fund-sensitive cases favour just-after-midnight or
        # late-morning; others get an idiosyncratic best hour.
        if reason.salary_sensitive:
            optimal_hour = int(rng.choice([0, 10, 11, 19]))
        else:
            optimal_hour = int(rng.integers(0, 24))

        latent = LatentCase(
            failure_id=failure.id,
            recoverability=reason.recoverability,
            ceiling=ceiling,
            retry_reach=_RETRY_REACH[reason.recoverability],
            optimal_hour=optimal_hour,
            salary_sensitive=reason.salary_sensitive,
            engagement=cust.engagement,
            salary_day=cust.salary_day,
            difficulty=float(np.clip(rng.normal(1.0, 0.08), 0.75, 1.2)),
        )
        self.latents[failure.id] = latent
        return latent

    def build_all(self, failures: list[FailureEvent]) -> None:
        for f in failures:
            self.build_latent(f)

    def latent(self, failure_id: str) -> LatentCase:
        return self.latents[failure_id]

    # -- resolution ---------------------------------------------------------- #
    def _bernoulli(self, p: float, *seed_parts: object) -> bool:
        rng = np.random.default_rng(_seed_from(self.seed, "resolve", *seed_parts))
        return bool(rng.random() < p)

    def resolve_retry(self, failure_id: str, at: datetime, attempt_number: int) -> bool:
        p = self.latent(failure_id).retry_prob(at, attempt_number)
        return self._bernoulli(p, failure_id, "retry", attempt_number, int(at.timestamp()))

    def resolve_dunning(
        self,
        failure_id: str,
        channel: Channel,
        language: Language,
        message_quality: float,
        attempt_number: int,
    ) -> bool:
        cust = self.customers[self._latent_customer_id(failure_id)]
        p = self.latent(failure_id).dunning_prob(channel, language, cust, message_quality)
        return self._bernoulli(p, failure_id, "dunning", channel.value, attempt_number)

    def _latent_customer_id(self, failure_id: str) -> str:
        # latents don't store the customer id; recover it via a reverse lookup cache
        return self._fid_to_customer[failure_id]

    def register_failures(self, failures: list[FailureEvent]) -> None:
        self._fid_to_customer = {f.id: f.customer_id for f in failures}
        self.build_all(failures)

    def probe_best_hour(self, failure_id: str, base_date: datetime) -> int:
        """Oracle: the truly optimal retry hour (used only for reporting/diagnostics)."""
        return self.latent(failure_id).optimal_hour
