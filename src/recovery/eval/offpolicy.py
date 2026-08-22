"""Off-policy (counterfactual) evaluation of the engine's decision policy.

This is the rigor most recovery vendors skip: proving a policy is better *without
deploying it*, using only logged data from a different (randomized) policy. It is
how large processors (e.g. Adyen, "Off-Policy Evaluation for Payments", arXiv
2501.10470) and Stripe validate interventions before an A/B test.

Setup — a clean single-step contextual-bandit evaluation of the engine's FIRST
action per failure:

* **Logging policy** μ: for each failure pick one action uniformly at random from
  {give_up, retry_now, retry_optimal, nudge}. Because it is uniform, the propensity
  μ(a|x) = 1/K is known exactly — the precondition every estimator below needs.
* **Target policy** π: the engine's deterministic first-action choice.
* We estimate V(π) = E[recovered | follow π] four ways and check they agree with the
  policy's *actual* on-policy value (a held-out ground-truth run):

    - DM   (Direct Method)      : reward model r̂(x,a), score π's action. Low var, biased.
    - IPS  (Inverse Propensity) : reweight logged reward by 1(a=π)/μ. Unbiased, high var.
    - SNIPS(self-normalized IPS): IPS with normalized weights. Lower variance.
    - DR   (Doubly Robust)      : DM baseline + IPS-corrected residual. Consistent if
                                  EITHER the reward model OR the propensities are right.

Refs: Dudík, Langford & Li, "Doubly Robust Policy Evaluation and Learning", ICML 2011.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from recovery.domain.models import ActionType
from recovery.eval.harness import build_case
from recovery.llm.dunning import DunningGenerator
from recovery.ml.features import case_feature_row
from recovery.ml.models import RecoveryModel, TimingModel, _DictGBM
from recovery.policy.bandit import ContextualBandit
from recovery.policy.engine import EngineConfig, RecoveryEngine

ACTIONS = ["give_up", "retry_now", "retry_optimal", "nudge"]
_K = len(ACTIONS)
_RETRY_HOUR = 10

# Map the engine's fine-grained action types onto the coarse OPE action set.
_ENGINE_TO_OPE = {
    ActionType.GIVE_UP: "give_up",
    ActionType.WAIT: "give_up",
    ActionType.RETRY_NOW: "retry_now",
    ActionType.RETRY_OPTIMAL: "retry_optimal",
    ActionType.DUNNING_NUDGE: "nudge",
    ActionType.REQUEST_CARD_UPDATE: "nudge",
    ActionType.SWITCH_METHOD: "nudge",
    ActionType.OFFER_GRACE: "nudge",
}


@dataclass
class OPEResult:
    logging_value: float          # mean reward of the random logging policy
    onpolicy_value: float         # engine's true single-step value (ground truth)
    dm: float
    ips: float
    snips: float
    dr: float
    n: int

    def as_dict(self) -> dict:
        return {
            "logging_policy_value": round(self.logging_value, 4),
            "engine_onpolicy_value": round(self.onpolicy_value, 4),
            "estimates": {
                "direct_method": round(self.dm, 4),
                "ips": round(self.ips, 4),
                "snips": round(self.snips, 4),
                "doubly_robust": round(self.dr, 4),
            },
            "n": self.n,
            "action_space": ACTIONS,
            "note": (
                "Single-step OPE of the engine's first action vs a uniform-random "
                "logging policy. IPS/SNIPS/DR estimate the engine's value from logged "
                "data alone; they should track engine_onpolicy_value."
            ),
        }


def _execute(action: str, case, env, timing_model: TimingModel) -> int:
    """Resolve one action against the hidden environment → recovered (0/1)."""
    f, c, s = case.failure, case.customer, case.subscription
    attempt = f.attempt_number + 1
    if action == "give_up":
        return 0
    if action == "retry_now":
        at = (f.occurred_at + timedelta(days=1)).replace(
            hour=_RETRY_HOUR, minute=0, second=0, microsecond=0
        )
        return int(env.resolve_retry(f.id, at, attempt))
    if action == "retry_optimal":
        best = timing_model.best_slot(
            f, c, s, f.occurred_at, attempt_number=attempt, horizon_days=14
        )
        return int(env.resolve_retry(f.id, best.when, attempt))
    if action == "nudge":
        return int(env.resolve_dunning(f.id, c.preferred_channel, c.language, 0.85, attempt))
    raise ValueError(action)


def evaluate_offpolicy(
    pop,
    recovery_model: RecoveryModel,
    timing_model: TimingModel,
    seed: int = 2024,
    max_failures: int | None = None,
) -> OPEResult:
    customers, subscriptions = pop.customers, pop.subscriptions
    rng = np.random.default_rng(seed)
    failures = pop.failures if max_failures is None else pop.failures[:max_failures]

    # One environment; resolve_* is content-hash-seeded so calls never collide.
    env = pop.environment()
    engine = RecoveryEngine(
        recovery_model,
        timing_model,
        dunning=DunningGenerator(force_templates=True),
        bandit=ContextualBandit(seed=seed),
        config=EngineConfig(),
    )

    rows: list[dict] = []          # reward-model features {**ctx, action}
    logged_a: list[str] = []
    logged_r: list[int] = []
    prop: list[float] = []
    ctx_rows: list[dict] = []      # context only (for scoring r̂(x, π))
    target_a: list[str] = []
    onpolicy_r: list[int] = []

    for f in failures:
        case = build_case(f, customers, subscriptions)
        ctx = case_feature_row(f, case.customer, case.subscription)

        # --- logging policy: uniform random action ---
        a_log = ACTIONS[int(rng.integers(_K))]
        r_log = _execute(a_log, case, env, timing_model)
        rows.append({**ctx, "action": a_log})
        logged_a.append(a_log)
        logged_r.append(r_log)
        prop.append(1.0 / _K)
        ctx_rows.append(ctx)

        # --- target policy: engine's first action ---
        decision = engine.plan(case)
        a_pi = _ENGINE_TO_OPE.get(decision.action_type, "nudge")
        target_a.append(a_pi)

        # --- ground-truth on-policy value of the engine's action ---
        onpolicy_r.append(_execute(a_pi, case, env, timing_model))

    logged_r_arr = np.array(logged_r, dtype=float)
    prop_arr = np.array(prop)
    match = np.array([a == t for a, t in zip(logged_a, target_a, strict=True)], dtype=float)

    # --- reward model r̂(x, a) for DM / DR ---
    reward_core = _DictGBM(random_state=seed)
    reward_core.fit(rows, logged_r_arr)
    r_hat_logged = np.array(reward_core.proba(rows))                       # r̂(x, a_logged)
    r_hat_target = np.array(reward_core.proba(
        [{**c, "action": t} for c, t in zip(ctx_rows, target_a, strict=True)]
    ))                                                                     # r̂(x, π(x))

    weights = match / prop_arr
    dm = float(r_hat_target.mean())
    ips = float((weights * logged_r_arr).mean())
    snips = float((weights * logged_r_arr).sum() / weights.sum()) if weights.sum() else 0.0
    dr = float((r_hat_target + weights * (logged_r_arr - r_hat_logged)).mean())

    return OPEResult(
        logging_value=float(logged_r_arr.mean()),
        onpolicy_value=float(np.mean(onpolicy_r)),
        dm=dm,
        ips=ips,
        snips=snips,
        dr=dr,
        n=len(failures),
    )
