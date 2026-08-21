"""Turn the population + environment into an *observational* training dataset.

A real merchant never gets clean labels; they get a messy log of "we retried at
some time / sent some email, and here's what happened." We reproduce exactly that
by running a **randomised logging policy** (scattered retries + a generic dunning)
through the hidden environment. The models then have to learn the true recovery
structure from this noisy log — no latents, no oracle.

Outputs two tables:

* ``timing`` — one row per retry *probe* at a random slot, labelled with whether
  that retry would have succeeded. Trains the optimal-timing model.
* ``cases`` — one row per failure, labelled with whether the logging policy ever
  recovered it (and how long it took). Trains the recovery-probability (triage)
  model.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from recovery.ml.features import case_feature_row, timing_feature_row
from recovery.simulation.generator import Population

# Hours a historical retrier realistically used (business hours + the midnight run).
_LOG_HOURS = [0, 1, 9, 10, 11, 13, 15, 18, 19, 21]


def build_training_logs(
    pop: Population,
    probes_per_case: int = 3,
    max_attempts: int = 3,
    horizon_days: int = 21,
    seed: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    env = pop.environment()
    rng = np.random.default_rng(seed + 101)

    timing_rows: list[dict] = []
    case_rows: list[dict] = []

    for fail in pop.failures:
        cust = pop.customers[fail.customer_id]
        sub = pop.subscriptions[fail.subscription_id]

        # --- timing probes: random independent (slot, attempt) retries ---------
        for _ in range(probes_per_case):
            day_offset = int(rng.integers(1, horizon_days + 1))
            hour = int(rng.choice(_LOG_HOURS))
            attempt = int(rng.choice([1, 2, 3], p=[0.6, 0.28, 0.12]))
            at = (fail.occurred_at + timedelta(days=day_offset)).replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
            row = timing_feature_row(fail, cust, sub, at, attempt)
            row["label"] = int(env.resolve_retry(fail.id, at, attempt))
            timing_rows.append(row)

        # --- case trajectory under the logging policy --------------------------
        recovered = False
        attempts = 0
        days_to_recover: float | None = None

        # scattered retry days + one generic dunning day, processed in time order
        retry_days = sorted(
            rng.choice(range(1, horizon_days + 1), size=max_attempts, replace=False).tolist()
        )
        dunning_day = int(rng.integers(1, horizon_days + 1))
        schedule = [(d, "retry") for d in retry_days] + [(dunning_day, "dunning")]
        schedule.sort()

        for i, (day_offset, kind) in enumerate(schedule, start=1):
            at = (fail.occurred_at + timedelta(days=day_offset)).replace(
                hour=int(rng.choice(_LOG_HOURS)), minute=0
            )
            attempts += 1
            if kind == "retry":
                ok = env.resolve_retry(fail.id, at, i)
            else:  # generic dunning: default channel, English, mediocre copy
                ok = env.resolve_dunning(
                    fail.id, cust.preferred_channel, cust.language, 0.8, i
                )
            if ok:
                recovered = True
                days_to_recover = float(day_offset)
                break

        crow = case_feature_row(fail, cust, sub)
        crow["label"] = int(recovered)
        crow["attempts"] = attempts
        crow["days_to_recover"] = days_to_recover if days_to_recover is not None else np.nan
        crow["failure_id"] = fail.id
        crow["amount_paise"] = fail.amount_paise
        case_rows.append(crow)

    return pd.DataFrame(timing_rows), pd.DataFrame(case_rows)
