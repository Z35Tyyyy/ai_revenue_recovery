"""Live recovery campaign — the engine actually *running*, streamed case-by-case.

This is what turns the static dashboard into a living system: a fresh cohort of
failed charges is streamed through the real engine (with a fresh bandit that learns
as it goes) racing a fixed-retry baseline on the *same* hidden ground truth. The
frontend animates the outcomes live. World-control presets reshape the failure mix
so you can watch the policy react — proof the results are computed, not canned.
"""

from __future__ import annotations

from collections.abc import Iterator

from recovery.domain.models import format_inr
from recovery.eval.executor import SimulatedExecutor
from recovery.eval.harness import _fixed_retry, build_case
from recovery.llm.dunning import DunningGenerator
from recovery.ml.models import RecoveryModel, TimingModel
from recovery.policy.bandit import ContextualBandit
from recovery.policy.engine import EngineConfig, RecoveryEngine
from recovery.simulation.generator import _REASON_MIX, generate_population


def _skew(**mult: float) -> dict[str, float]:
    m = dict(_REASON_MIX)
    for k, f in mult.items():
        m[k] = m.get(k, 0.02) * f
    return m


# World-control presets: reshape the failure population and watch the engine adapt.
SCENARIOS: dict[str, dict[str, float] | None] = {
    "balanced": None,
    "expired_cards": _skew(
        card_expired=6, card_disabled=4, international_transaction_not_allowed=3
    ),
    "insufficient_funds": _skew(insufficient_funds=3.5),
    "hard_declines": _skew(invalid_card=6, stolen_or_lost_card=6, payer_account_frozen=6),
    "mandate_issues": _skew(mandate_paused=6, mandate_revoked=6, authentication_failed=4),
}


def _rate(rec: int, tot: int) -> float:
    return round(rec / tot, 4) if tot else 0.0


def run_campaign(
    recovery_model: RecoveryModel,
    timing_model: TimingModel,
    n: int = 100,
    scenario: str = "balanced",
    seed: int = 20260823,
) -> Iterator[dict]:
    """Stream a live recovery campaign. Yields one event per processed failure plus a
    final ``done`` event. The engine's bandit learns online as the stream progresses."""
    n = max(10, min(400, int(n)))
    mix = SCENARIOS.get(scenario, None)
    pop = generate_population(
        n_customers=max(200, n), n_failures=n, seed=seed, reason_mix=mix
    )
    env = pop.environment()
    executor = SimulatedExecutor(env)
    bandit = ContextualBandit(seed=seed)  # fresh — you watch it learn
    engine = RecoveryEngine(
        recovery_model,
        timing_model,
        dunning=DunningGenerator(force_templates=True),
        bandit=bandit,
        config=EngineConfig(),
    )

    e_rec = e_rev = e_retries = e_msgs = 0
    b_rec = b_rev = b_retries = 0
    total = tot_rev = 0

    yield {"type": "start", "n": n, "scenario": scenario}

    for i, f in enumerate(pop.failures):
        case = build_case(f, pop.customers, pop.subscriptions)
        outcome = engine.run_episode(case, executor)  # updates the bandit online
        base = _fixed_retry(case, env)

        retries = sum(1 for a in case.actions if a.type.value.startswith("retry"))
        e_retries += retries
        e_msgs += len(case.actions) - retries
        b_retries += base.retries
        total += 1
        tot_rev += f.amount_paise
        if outcome.recovered:
            e_rec += 1
            e_rev += f.amount_paise
        if base.recovered:
            b_rec += 1
            b_rev += f.amount_paise

        first = case.actions[0].type.value if case.actions else "give_up"
        ev = {
            "type": "case",
            "i": i,
            "case": {
                "id": case.id,
                "reason": f.reason_code,
                "class": case.recoverability_class.value,
                "amount_paise": f.amount_paise,
                "amount": format_inr(f.amount_paise),
                "city": case.customer.city,
                "language": case.customer.language.value,
                "method": f.method.value,
            },
            "engine": {"action": first, "recovered": outcome.recovered},
            "baseline": {"recovered": base.recovered},
            "totals": {
                "n": total,
                "total_revenue_paise": tot_rev,
                "engine": {
                    "recovered": e_rec, "rate": _rate(e_rec, total),
                    "revenue_paise": e_rev, "retries": e_retries, "messages": e_msgs,
                },
                "baseline": {
                    "recovered": b_rec, "rate": _rate(b_rec, total),
                    "revenue_paise": b_rev, "retries": b_retries,
                },
            },
        }
        # Periodically attach what the bandit has learned so far (visible learning).
        if i % 10 == 0 or i == n - 1:
            ev["bandit"] = bandit.snapshot()
        yield ev

    yield {
        "type": "done",
        "summary": {
            "engine_rate": _rate(e_rec, total),
            "baseline_rate": _rate(b_rec, total),
            "uplift_pts": round((_rate(e_rec, total) - _rate(b_rec, total)) * 100, 1),
            "engine_revenue_paise": e_rev,
            "baseline_revenue_paise": b_rev,
            "engine_retries": e_retries,
            "baseline_retries": b_retries,
            "bandit": bandit.snapshot(),
        },
    }
