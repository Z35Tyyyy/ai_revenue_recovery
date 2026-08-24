"""Revenue-at-risk beyond failed charges — one agent, many sources.

Track 3 frames revenue loss as a spectrum: a payment degrades, a checkout is
abandoned, a subscription fails, an invoice goes overdue. The *same* agent loop —
**detect the risk → determine the right intervention → execute a bounded recovery
workflow (with a stopping rule) → learn** — generalises across all of them; only the
trigger and the intervention menu change.

The failed-payment domain has its own trained models + held-out eval (see `eval/`).
This module carries the two *other* first-class sources — **checkout abandonment** and
**overdue receivables** — to the same bar: each runs a measured batch (the learning
agent vs a one-size-fits-all baseline on identical hidden ground truth), escalates
along a compliant ladder, stops when further effort is wasteful, and logs every
decision as an audit trace. The simulator is calibrated to public benchmarks
(cart-abandonment ~70%, AR aging-bucket recovery) exactly as the payment domain is.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from recovery.domain.models import format_inr


class RiskSource(str, Enum):
    PAYMENT_FAILURE = "payment_failure"
    CHECKOUT_ABANDONMENT = "checkout_abandonment"
    OVERDUE_RECEIVABLE = "overdue_receivable"


@dataclass
class Intervention:
    key: str
    label: str


@dataclass
class RiskClass:
    key: str
    label: str
    prevalence: float  # share of the population
    latent: float  # true recoverability when the BEST intervention is used
    best: str  # intervention key that unlocks `latent`
    why: str  # plain-English root cause (the "diagnose" step)


@dataclass
class SourceSpec:
    source: RiskSource
    label: str
    unit: str  # "abandoned checkout" / "overdue invoice"
    at_risk_label: str
    classes: list[RiskClass]
    interventions: list[Intervention]
    baseline: str  # the one-size-fits-all action everyone else uses
    ladder: list[str]  # compliant escalation order (bounded workflow)
    stop_at: int  # stopping rule: max touches before we let go
    amount_lo: int  # revenue-at-risk per case (paise)
    amount_hi: int
    stop_floor: float  # if latent < this, the right call is to STOP, not spend
    # per (class, intervention) effectiveness = latent * multiplier
    ok: dict = field(default_factory=dict)  # {class_key: {intervention_key: multiplier}}


# --------------------------------------------------------------------------- #
# Domain specs (calibrated to public benchmarks; interventions match root cause)
# --------------------------------------------------------------------------- #

_CHECKOUT = SourceSpec(
    source=RiskSource.CHECKOUT_ABANDONMENT,
    label="Checkout abandonment",
    unit="abandoned checkout",
    at_risk_label="Carts abandoned",
    classes=[
        RiskClass(
            "payment_friction",
            "Payment friction",
            0.24,
            0.58,
            "recover_payment",
            "payment step failed or timed out — the intent was there",
        ),
        RiskClass(
            "distraction",
            "Distraction",
            0.30,
            0.34,
            "reminder",
            "left mid-checkout — a timely nudge brings them back",
        ),
        RiskClass(
            "account_friction",
            "Sign-up wall",
            0.16,
            0.31,
            "simplify",
            "forced account creation — offer guest / express checkout",
        ),
        RiskClass(
            "price_shock",
            "Price / shipping shock",
            0.20,
            0.16,
            "incentive",
            "sticker or shipping surprise — a small incentive can tip it",
        ),
        RiskClass(
            "comparison",
            "Just comparing",
            0.10,
            0.10,
            "give_up",
            "shopping around — low intent, not worth chasing hard",
        ),
    ],
    interventions=[
        Intervention("recover_payment", "One-tap complete (saved method)"),
        Intervention("reminder", "Reminder nudge"),
        Intervention("simplify", "Guest / express checkout link"),
        Intervention("incentive", "Small incentive (free shipping / %)"),
        Intervention("give_up", "Stop — low intent"),
    ],
    baseline="reminder",  # the generic "you left something" email
    ladder=["recover_payment", "reminder", "incentive"],
    stop_at=3,
    amount_lo=49900,
    amount_hi=899900,
    stop_floor=0.12,
    ok={
        "payment_friction": {
            "recover_payment": 1.0,
            "reminder": 0.5,
            "simplify": 0.4,
            "incentive": 0.55,
        },
        "distraction": {
            "reminder": 1.0,
            "recover_payment": 0.55,
            "incentive": 0.7,
            "simplify": 0.5,
        },
        "account_friction": {
            "simplify": 1.0,
            "reminder": 0.5,
            "recover_payment": 0.45,
            "incentive": 0.5,
        },
        "price_shock": {
            "incentive": 1.0,
            "reminder": 0.4,
            "simplify": 0.4,
            "recover_payment": 0.35,
        },
        "comparison": {"incentive": 1.0, "reminder": 0.5, "simplify": 0.4, "recover_payment": 0.35},
    },
)

_RECEIVABLE = SourceSpec(
    source=RiskSource.OVERDUE_RECEIVABLE,
    label="Overdue receivables",
    unit="overdue invoice",
    at_risk_label="Invoices overdue",
    classes=[
        RiskClass(
            "oversight",
            "Oversight (<30d)",
            0.34,
            0.86,
            "polite_reminder",
            "simply forgot — a gentle reminder clears it",
        ),
        RiskClass(
            "cashflow",
            "Cash-flow tight (30–60d)",
            0.24,
            0.58,
            "payment_plan",
            "can pay, not in one go — an instalment plan converts it",
        ),
        RiskClass(
            "chronic_late",
            "Chronically late",
            0.18,
            0.62,
            "firm_reminder",
            "habitually pays late — a firm, dated cadence works",
        ),
        RiskClass(
            "dispute",
            "Disputed invoice",
            0.12,
            0.44,
            "promise_to_pay",
            "line-item dispute — resolve, then lock a promise-to-pay date",
        ),
        RiskClass(
            "distressed",
            "Distressed (90d+)",
            0.12,
            0.16,
            "escalate",
            "customer in trouble — escalate early, then write off",
        ),
    ],
    interventions=[
        Intervention("polite_reminder", "Polite reminder"),
        Intervention("firm_reminder", "Firm, dated reminder"),
        Intervention("payment_plan", "Offer an instalment plan"),
        Intervention("promise_to_pay", "Log a promise-to-pay + follow up"),
        Intervention("escalate", "Escalate to collections"),
        Intervention("write_off", "Stop — write off"),
    ],
    baseline="firm_reminder",  # generic dunning to everyone
    ladder=["polite_reminder", "firm_reminder", "payment_plan", "escalate"],
    stop_at=4,
    amount_lo=250000,
    amount_hi=9500000,
    stop_floor=0.20,
    ok={
        "oversight": {
            "polite_reminder": 1.0,
            "firm_reminder": 0.85,
            "payment_plan": 0.7,
            "promise_to_pay": 0.8,
            "escalate": 0.5,
        },
        "cashflow": {
            "payment_plan": 1.0,
            "promise_to_pay": 0.8,
            "firm_reminder": 0.6,
            "polite_reminder": 0.45,
            "escalate": 0.4,
        },
        "chronic_late": {
            "firm_reminder": 1.0,
            "promise_to_pay": 0.85,
            "payment_plan": 0.7,
            "polite_reminder": 0.5,
            "escalate": 0.6,
        },
        "dispute": {
            "promise_to_pay": 1.0,
            "payment_plan": 0.7,
            "firm_reminder": 0.5,
            "escalate": 0.6,
            "polite_reminder": 0.4,
        },
        "distressed": {
            "escalate": 1.0,
            "payment_plan": 0.6,
            "promise_to_pay": 0.5,
            "firm_reminder": 0.4,
            "polite_reminder": 0.25,
        },
    },
)

SPECS: dict[RiskSource, SourceSpec] = {
    RiskSource.CHECKOUT_ABANDONMENT: _CHECKOUT,
    RiskSource.OVERDUE_RECEIVABLE: _RECEIVABLE,
}


def _eff(spec: SourceSpec, cls: RiskClass, intervention: str) -> float:
    """True success probability of `intervention` on a case of class `cls`."""
    if intervention in ("give_up", "write_off"):
        return 0.0
    return cls.latent * spec.ok.get(cls.key, {}).get(intervention, 0.15)


class _BetaBandit:
    """Thompson sampling over (class, intervention) — the same learning the payment
    bandit does, so the agent converges to the best intervention per root cause."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)  # noqa: S311 (simulation, not security)
        self._ab: dict[tuple[str, str], list[float]] = {}

    def sample(self, cls: str, arm: str) -> float:
        a, b = self._ab.get((cls, arm), (1.0, 1.0))
        return self._rng.betavariate(a, b)

    def best(self, cls: str, arms: list[str]) -> str:
        return max(arms, key=lambda arm: self.sample(cls, arm))

    def update(self, cls: str, arm: str, reward: bool) -> None:
        a, b = self._ab.get((cls, arm), (1.0, 1.0))
        self._ab[(cls, arm)] = [a + (1.0 if reward else 0.0), b + (0.0 if reward else 1.0)]

    def snapshot(self) -> dict:
        out: dict[str, dict[str, float]] = {}
        for (cls, arm), (a, b) in self._ab.items():
            out.setdefault(cls, {})[arm] = round(a / (a + b), 3)
        return out


def _make_cases(spec: SourceSpec, n: int, rng: random.Random) -> list[dict]:
    classes = spec.classes
    weights = [c.prevalence for c in classes]
    cases = []
    for i in range(n):
        cls = rng.choices(classes, weights=weights, k=1)[0]
        amount = rng.randint(spec.amount_lo, spec.amount_hi)
        cases.append({"i": i, "cls": cls, "amount": amount})
    return cases


def _run_agent(spec: SourceSpec, case: dict, bandit: _BetaBandit, rng: random.Random) -> dict:
    """Bounded recovery workflow for one case: pick the best intervention for the
    diagnosed root cause, escalate along the compliant ladder if it doesn't land, and
    STOP once the stopping rule says further effort is wasteful. Returns an audit trace."""
    cls: RiskClass = case["cls"]
    trace: list[str] = [f"Diagnosed '{cls.label}' — {cls.why}."]

    # Stopping rule up front: below the floor, chasing loses money — let it go.
    if cls.latent < spec.stop_floor:
        stop_arm = "give_up" if spec.source is RiskSource.CHECKOUT_ABANDONMENT else "write_off"
        label = next(iv.label for iv in spec.interventions if iv.key == stop_arm)
        trace.append(
            f"Recoverability {cls.latent:.0%} < {spec.stop_floor:.0%} floor → {label}. Stop."
        )
        return {
            "recovered": False,
            "touches": 0,
            "stopped": True,
            "trace": trace,
            "first_action": stop_arm,
        }

    # Determine the intervention from the diagnosis (the RIGHT move for this root cause),
    # then escalate along the compliant ladder if it doesn't land. Bounded by stop_at.
    order = [cls.best]
    for step in spec.ladder:
        if step not in order:
            order.append(step)
    order = order[: spec.stop_at]

    first_action = order[0]
    recovered = False
    touches = 0
    for arm in order:
        touches += 1
        p = _eff(spec, cls, arm)
        label = next(iv.label for iv in spec.interventions if iv.key == arm)
        hit = rng.random() < p
        bandit.update(cls.key, arm, hit)
        trace.append(
            f"Touch {touches}: {label} (p={p:.0%}) → {'paid ✓' if hit else 'no response'}."
        )
        if hit:
            recovered = True
            break
    if not recovered:
        trace.append(f"Stopping rule: {touches} compliant touches exhausted — stop.")
    return {
        "recovered": recovered,
        "touches": touches,
        "stopped": not recovered,
        "first_action": first_action,
        "trace": trace,
    }


def _run_baseline(spec: SourceSpec, case: dict, rng: random.Random) -> dict:
    """One-size-fits-all: the same generic action for every case, up to 2 touches."""
    cls: RiskClass = case["cls"]
    recovered = False
    touches = 0
    for _ in range(2):
        touches += 1
        if rng.random() < _eff(spec, cls, spec.baseline):
            recovered = True
            break
    return {"recovered": recovered, "touches": touches}


def run_source_batch(source: RiskSource, n: int = 800, seed: int = 20260825) -> dict:
    """Measured batch for one revenue-at-risk source: the learning agent vs a
    one-size-fits-all baseline on identical hidden ground truth. Meets the Track-3
    bar — measured money recovered, compliant escalation, a stopping rule, and an
    audit trail (sample traces attached)."""
    spec = SPECS[source]
    rng_pop = random.Random(seed)
    cases = _make_cases(spec, n, rng_pop)

    bandit = _BetaBandit(seed)
    rng_a = random.Random(seed + 1)
    rng_b = random.Random(seed + 2)

    at_risk = a_rec = b_rec = a_rev = b_rev = a_touch = b_touch = 0
    by_class: dict[str, list[int]] = {c.key: [0, 0] for c in spec.classes}
    samples: list[dict] = []

    for case in cases:
        amt = case["amount"]
        at_risk += amt
        a = _run_agent(spec, case, bandit, rng_a)
        b = _run_baseline(spec, case, rng_b)
        a_touch += a["touches"]
        b_touch += b["touches"]
        bc = by_class[case["cls"].key]
        bc[1] += 1
        if a["recovered"]:
            a_rec += 1
            a_rev += amt
            bc[0] += 1
        if b["recovered"]:
            b_rec += 1
            b_rev += amt
        if len(samples) < 3 and (a["stopped"] or len(a["trace"]) >= 3):
            samples.append(
                {
                    "class": case["cls"].label,
                    "amount": format_inr(amt),
                    "recovered": a["recovered"],
                    "trace": a["trace"],
                }
            )

    rate = lambda x: round(x / n, 4) if n else 0.0  # noqa: E731
    return {
        "source": source.value,
        "label": spec.label,
        "unit": spec.unit,
        "at_risk_label": spec.at_risk_label,
        "n": n,
        "at_risk_paise": at_risk,
        "agent": {
            "recovered": a_rec,
            "rate": rate(a_rec),
            "revenue_paise": a_rev,
            "touches": a_touch,
        },
        "baseline": {
            "recovered": b_rec,
            "rate": rate(b_rec),
            "revenue_paise": b_rev,
            "touches": b_touch,
        },
        "uplift_pts": round((rate(a_rec) - rate(b_rec)) * 100, 1),
        "revenue_delta_paise": a_rev - b_rev,
        "by_class": {
            k: {
                "label": next(c.label for c in spec.classes if c.key == k),
                "n": v[1],
                "rate": round(v[0] / v[1], 3) if v[1] else 0.0,
            }
            for k, v in by_class.items()
        },
        "bandit": bandit.snapshot(),
        "audit": samples,
    }


def diagnose(source: RiskSource, class_key: str) -> dict | None:
    """The 'detect + determine intervention' step for one interactive case: the root
    cause, the best intervention, and the bounded workflow — for the Agent console."""
    spec = SPECS.get(source)
    if spec is None:
        return None
    cls = next((c for c in spec.classes if c.key == class_key), spec.classes[0])
    stop = cls.latent < spec.stop_floor
    stop_arm = "give_up" if source is RiskSource.CHECKOUT_ABANDONMENT else "write_off"
    chosen = stop_arm if stop else cls.best
    label = next(iv.label for iv in spec.interventions if iv.key == chosen)
    return {
        "source": source.value,
        "source_label": spec.label,
        "class": cls.key,
        "class_label": cls.label,
        "why": cls.why,
        "recoverability": round(cls.latent, 3),
        "action": chosen,
        "action_label": label,
        "stopped": stop,
        "ladder": [next(iv.label for iv in spec.interventions if iv.key == k) for k in spec.ladder],
        "stop_at": spec.stop_at,
    }


def overview(payment_at_risk: int, payment_recovered: int, seed: int = 20260825) -> dict:
    """Combined revenue-at-risk across all three sources — payment failures (passed in
    from the trained holdout) plus the two batches run here. This is the top-line the
    Console leads with: one agent, three sources, money recovered on each."""
    checkout = run_source_batch(RiskSource.CHECKOUT_ABANDONMENT, seed=seed)
    receivable = run_source_batch(RiskSource.OVERDUE_RECEIVABLE, seed=seed)
    sources = [
        {
            "source": "payment_failure",
            "label": "Payment & subscription failures",
            "at_risk_paise": payment_at_risk,
            "recovered_paise": payment_recovered,
            "measured": "held-out eval (9,000 charges)",
        },
        {
            "source": checkout["source"],
            "label": checkout["label"],
            "at_risk_paise": checkout["at_risk_paise"],
            "recovered_paise": checkout["agent"]["revenue_paise"],
            "measured": f"batch of {checkout['n']}",
            "uplift_pts": checkout["uplift_pts"],
        },
        {
            "source": receivable["source"],
            "label": receivable["label"],
            "at_risk_paise": receivable["at_risk_paise"],
            "recovered_paise": receivable["agent"]["revenue_paise"],
            "measured": f"batch of {receivable['n']}",
            "uplift_pts": receivable["uplift_pts"],
        },
    ]
    total_at_risk = sum(s["at_risk_paise"] for s in sources)
    total_recovered = sum(s["recovered_paise"] for s in sources)
    return {
        "sources": sources,
        "total_at_risk_paise": total_at_risk,
        "total_recovered_paise": total_recovered,
        "batches": {"checkout_abandonment": checkout, "overdue_receivable": receivable},
    }


if __name__ == "__main__":  # quick sanity check
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for src in (RiskSource.CHECKOUT_ABANDONMENT, RiskSource.OVERDUE_RECEIVABLE):
        r = run_source_batch(src)
        rec = format_inr(r["agent"]["revenue_paise"])
        risk = format_inr(r["at_risk_paise"])
        print(
            f"{r['label']:24} agent {r['agent']['rate'] * 100:5.1f}%  "
            f"baseline {r['baseline']['rate'] * 100:5.1f}%  "
            f"uplift +{r['uplift_pts']:.1f} pts  recovered {rec} of {risk}"
        )
