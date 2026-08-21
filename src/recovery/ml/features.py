"""Feature extraction — the single source of truth used by BOTH training and serving.

Two rules keep the whole evaluation honest:

1. **Observable only.** We never read a latent (true engagement, ceiling, optimal
   hour). The models must earn their signal from what a merchant actually sees:
   the failure reason, instrument, amount, tenure, and — India's killer feature —
   the *estimated salary day* the customer tends to be paid on.
2. **Symmetry.** The exact same functions build the training matrix and the
   live-scoring vector, so there is no train/serve skew. Rows are plain dicts;
   a fitted :class:`~sklearn.feature_extraction.DictVectorizer` (saved with each
   model) turns them into arrays and one-hots the categoricals.
"""

from __future__ import annotations

import math
from datetime import datetime

from recovery.domain.models import Customer, FailureEvent, Subscription
from recovery.domain.taxonomy import classify_reason


def days_since_salary(day_of_month: int, salary_day: int) -> int:
    """Whole days since payday (0 == payday), wrapped into a ~30-day month."""
    diff = day_of_month - salary_day
    if diff < 0:
        diff += 30
    return diff


def case_feature_row(
    failure: FailureEvent, customer: Customer, subscription: Subscription
) -> dict[str, float | str]:
    """Observable features describing a failed charge — no timing, no latents."""
    reason = classify_reason(failure.reason_code)
    return {
        # --- what failed (the strongest signal) ---
        "reason": failure.reason_code,
        "recoverability": reason.recoverability.value,
        "prior_recover_prob": float(reason.prior_recover_prob),
        "retry_helps": 1.0 if reason.retry_helps else 0.0,
        "salary_sensitive": 1.0 if reason.salary_sensitive else 0.0,
        # --- how it was being charged ---
        "method": failure.method.value,
        "log_amount": math.log1p(failure.amount_paise / 100.0),
        "attempt_number": float(failure.attempt_number),
        # --- who the customer is (proxies for the hidden 'will they pay' latent) ---
        "tenure_months": float(customer.tenure_months),
        "log_ltv": math.log1p(customer.lifetime_value_paise / 100.0),
        "language": customer.language.value,
        "preferred_channel": customer.preferred_channel.value,
        "city": customer.city,
    }


def _cyc(value: float, period: float) -> tuple[float, float]:
    ang = 2 * math.pi * (value / period)
    return math.sin(ang), math.cos(ang)


def timing_feature_row(
    failure: FailureEvent,
    customer: Customer,
    subscription: Subscription,
    at_time: datetime,
    attempt_number: int,
) -> dict[str, float | str]:
    """Case features + the candidate retry *slot*, for the optimal-timing model."""
    row = case_feature_row(failure, customer, subscription)
    row["attempt_number"] = float(attempt_number)

    hour_sin, hour_cos = _cyc(at_time.hour, 24)
    dow_sin, dow_cos = _cyc(at_time.weekday(), 7)
    dsl = days_since_salary(at_time.day, customer.salary_day)
    # days between the original failure and this candidate retry
    day_offset = max(0, (at_time.date() - failure.occurred_at.date()).days)

    row.update(
        {
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "dow_sin": dow_sin,
            "dow_cos": dow_cos,
            "is_night": 1.0 if at_time.hour in (0, 1, 2, 23) else 0.0,
            "days_since_salary": float(dsl),
            "near_salary": 1.0 if dsl <= 2 else 0.0,
            "day_offset": float(day_offset),
            # interaction the model would otherwise have to discover the hard way
            "salary_x_dsl": (1.0 if row["salary_sensitive"] else 0.0) * float(dsl),
        }
    )
    return row
