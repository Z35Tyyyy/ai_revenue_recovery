"""Held-out evaluation: the engine vs. realistic baselines, on ground truth.

The whole point of the project lives here. We freeze a fresh population the models
have never seen, then run four policies through the *same* hidden environment:

* ``no_action``      — no recovery program at all (the floor).
* ``fixed_retry``    — retry next day at 10:00 for a few days (Razorpay's default).
* ``generic_dunning``— fixed retries + one generic English email blast.
* ``engine``         — our agentic engine (ML timing + smart actions + bandit).

Because every policy faces identical latents, the gap between them is real,
attributable skill — not luck and not leakage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sklearn.metrics import roc_auc_score

from recovery.domain.models import (
    RecoverabilityClass,
    RecoveryCase,
    format_inr,
)
from recovery.domain.taxonomy import classify_reason
from recovery.eval.executor import SimulatedExecutor
from recovery.llm.dunning import DunningGenerator
from recovery.ml.models import RecoveryModel, TimingModel
from recovery.policy.bandit import ContextualBandit
from recovery.policy.engine import EngineConfig, RecoveryEngine
from recovery.simulation.environment import RecoveryEnvironment
from recovery.simulation.generator import Population

_RETRY_HOUR = 10
_FIXED_RETRY_DAYS = 4


def build_case(failure, customers, subscriptions) -> RecoveryCase:
    return RecoveryCase(
        id=f"case_{failure.id}",
        failure=failure,
        customer=customers[failure.customer_id],
        subscription=subscriptions[failure.subscription_id],
    )


@dataclass
class CaseOutcome:
    recovered: bool
    amount_paise: int
    days: float | None
    retries: int
    nudges: int
    reason_class: RecoverabilityClass


@dataclass
class PolicyMetrics:
    name: str
    total: int = 0
    recovered: int = 0
    revenue_total_paise: int = 0
    revenue_recovered_paise: int = 0
    retries: int = 0
    nudges: int = 0
    _days: list[float] = field(default_factory=list)
    _by_class: dict[str, list[int]] = field(default_factory=dict)  # class -> [rec, total]

    def add(self, o: CaseOutcome) -> None:
        self.total += 1
        self.revenue_total_paise += o.amount_paise
        self.retries += o.retries
        self.nudges += o.nudges
        bc = self._by_class.setdefault(o.reason_class.value, [0, 0])
        bc[1] += 1
        if o.recovered:
            self.recovered += 1
            self.revenue_recovered_paise += o.amount_paise
            bc[0] += 1
            if o.days is not None:
                self._days.append(o.days)

    @property
    def recovery_rate(self) -> float:
        return self.recovered / self.total if self.total else 0.0

    @property
    def revenue_recovery_rate(self) -> float:
        return (
            self.revenue_recovered_paise / self.revenue_total_paise
            if self.revenue_total_paise
            else 0.0
        )

    @property
    def avg_days_to_recover(self) -> float | None:
        return sum(self._days) / len(self._days) if self._days else None

    @property
    def messages_sent(self) -> int:
        return self.nudges

    def by_class_rate(self) -> dict[str, float]:
        return {k: (v[0] / v[1] if v[1] else 0.0) for k, v in sorted(self._by_class.items())}

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "total": self.total,
            "recovered": self.recovered,
            "recovery_rate": round(self.recovery_rate, 4),
            "revenue_total_paise": self.revenue_total_paise,
            "revenue_recovered_paise": self.revenue_recovered_paise,
            "revenue_recovery_rate": round(self.revenue_recovery_rate, 4),
            "avg_days_to_recover": (
                round(self.avg_days_to_recover, 2)
                if self.avg_days_to_recover is not None
                else None
            ),
            "retries": self.retries,
            "nudges": self.nudges,
            "by_class_rate": self.by_class_rate(),
        }


@dataclass
class EvalResult:
    policies: dict[str, PolicyMetrics]
    engine_prediction_auc: float
    bandit: dict
    sample_cases: list[dict]

    def uplift_vs(self, base: str, target: str) -> dict:
        b, t = self.policies[base], self.policies[target]
        return {
            "recovery_rate_abs": round(t.recovery_rate - b.recovery_rate, 4),
            "recovery_rate_rel": round(
                (t.recovery_rate - b.recovery_rate) / b.recovery_rate, 4
            )
            if b.recovery_rate
            else None,
            "revenue_recovered_delta_paise": t.revenue_recovered_paise
            - b.revenue_recovered_paise,
        }

    def as_dict(self) -> dict:
        return {
            "policies": {k: v.as_dict() for k, v in self.policies.items()},
            "engine_prediction_auc": round(self.engine_prediction_auc, 4),
            "bandit": self.bandit,
            "sample_cases": self.sample_cases,
        }


# --------------------------------------------------------------------------- #
# Baseline policies (resolved directly against the environment)
# --------------------------------------------------------------------------- #
def _no_action(case: RecoveryCase, env: RecoveryEnvironment) -> CaseOutcome:
    reason = classify_reason(case.failure.reason_code)
    return CaseOutcome(False, case.failure.amount_paise, None, 0, 0, reason.recoverability)


def _fixed_retry(case: RecoveryCase, env: RecoveryEnvironment) -> CaseOutcome:
    reason = classify_reason(case.failure.reason_code)
    t0 = case.failure.occurred_at
    retries = 0
    for day in range(1, _FIXED_RETRY_DAYS + 1):
        retries += 1
        at = (t0 + timedelta(days=day)).replace(hour=_RETRY_HOUR, minute=0, second=0, microsecond=0)
        if env.resolve_retry(case.failure.id, at, day):
            return CaseOutcome(True, case.failure.amount_paise, float(day), retries, 0,
                               reason.recoverability)
    return CaseOutcome(False, case.failure.amount_paise, None, retries, 0, reason.recoverability)


def _generic_dunning(case: RecoveryCase, env: RecoveryEnvironment) -> CaseOutcome:
    """Fixed retries + one generic-copy dunning at day 2 (quality 0.8).

    Fair baseline: the message goes on the customer's own preferred channel and
    language (same as the engine), so the comparison measures the engine's *action
    selection* — not a rigged English-email channel handicap.
    """
    reason = classify_reason(case.failure.reason_code)
    cust = case.customer
    t0 = case.failure.occurred_at
    schedule = [(1, "retry"), (2, "retry"), (2, "dunning"), (3, "retry"), (4, "retry")]
    retries = nudges = 0
    for i, (day, kind) in enumerate(schedule, start=1):
        at = (t0 + timedelta(days=day)).replace(hour=_RETRY_HOUR, minute=0, second=0, microsecond=0)
        if kind == "retry":
            retries += 1
            ok = env.resolve_retry(case.failure.id, at, day)
        else:
            nudges += 1
            ok = env.resolve_dunning(
                case.failure.id, cust.preferred_channel, cust.language, 0.8, attempt_number=i
            )
        if ok:
            return CaseOutcome(True, case.failure.amount_paise, float(day), retries, nudges,
                               reason.recoverability)
    return CaseOutcome(
        False, case.failure.amount_paise, None, retries, nudges, reason.recoverability
    )


def _fixed_retry_14d(case: RecoveryCase, env: RecoveryEnvironment) -> CaseOutcome:
    """Window-matched control: naive daily retry over the SAME 14-day horizon the
    engine is given — isolates genuine timing skill from mere window length."""
    reason = classify_reason(case.failure.reason_code)
    t0 = case.failure.occurred_at
    retries = 0
    for day in range(1, 15):
        retries += 1
        at = (t0 + timedelta(days=day)).replace(hour=_RETRY_HOUR, minute=0, second=0, microsecond=0)
        if env.resolve_retry(case.failure.id, at, day):
            return CaseOutcome(True, case.failure.amount_paise, float(day), retries, 0,
                               reason.recoverability)
    return CaseOutcome(False, case.failure.amount_paise, None, retries, 0, reason.recoverability)


# --------------------------------------------------------------------------- #
# Evaluation driver
# --------------------------------------------------------------------------- #
def evaluate(
    pop: Population,
    recovery_model: RecoveryModel,
    timing_model: TimingModel,
    config: EngineConfig | None = None,
    seed: int = 7,
    n_sample_traces: int = 6,
) -> EvalResult:
    customers, subscriptions = pop.customers, pop.subscriptions
    baselines = {
        "no_action": _no_action,
        "fixed_retry": _fixed_retry,
        "fixed_retry_14d": _fixed_retry_14d,
        "generic_dunning": _generic_dunning,
    }
    metrics = {name: PolicyMetrics(name=name) for name in [*baselines, "engine"]}

    # --- baselines: each needs its OWN environment so seeded draws don't collide ---
    for name, fn in baselines.items():
        env = pop.environment()  # rebuilt latents identical across policies (same seed)
        for f in pop.failures:
            metrics[name].add(fn(build_case(f, customers, subscriptions), env))

    # --- engine ---
    env = pop.environment()
    executor = SimulatedExecutor(env)
    bandit = ContextualBandit(seed=seed)
    engine = RecoveryEngine(
        recovery_model,
        timing_model,
        # Force templates so evaluation is offline, fast, and reproducible
        # regardless of any configured LLM key.
        dunning=DunningGenerator(force_templates=True),
        bandit=bandit,
        config=config or EngineConfig(),
    )

    y_true: list[int] = []
    y_pred: list[float] = []
    sample_cases: list[dict] = []
    for f in pop.failures:
        case = build_case(f, customers, subscriptions)
        outcome = engine.run_episode(case, executor)
        retries = sum(1 for a in case.actions if a.type.value.startswith("retry"))
        nudges = len(case.actions) - retries
        metrics["engine"].add(
            CaseOutcome(
                outcome.recovered,
                f.amount_paise,
                outcome.days_to_recover,
                retries,
                nudges,
                case.recoverability_class,
            )
        )
        y_true.append(int(outcome.recovered))
        y_pred.append(case.predicted_recover_prob or 0.0)
        if len(sample_cases) < n_sample_traces and case.actions:
            sample_cases.append(
                {
                    "case_id": case.id,
                    "reason": f.reason_code,
                    "class": case.recoverability_class.value,
                    "amount": format_inr(f.amount_paise),
                    "language": case.customer.language.value,
                    "channel": case.customer.preferred_channel.value,
                    "recovered": outcome.recovered,
                    "predicted_recover_prob": round(case.predicted_recover_prob or 0.0, 3),
                    "trace": case.trace,
                }
            )

    auc = roc_auc_score(y_true, y_pred) if len(set(y_true)) > 1 else float("nan")
    return EvalResult(
        policies=metrics,
        engine_prediction_auc=float(auc),
        bandit=bandit.snapshot(),
        sample_cases=sample_cases,
    )
