"""Synthetic-but-realistic subscription population + failed-payment stream.

Deliberately India-native: WhatsApp-first channels, salary days clustered on the
1st/7th/25th/last, UPI-autopay heavily represented, plan prices in familiar rupee
tiers, and a failure-reason mix that looks like a real recurring book (insufficient
funds and do-not-honour dominate; hard declines are rare).

Everything is seeded, so ``generate_population(seed=7)`` is byte-for-byte stable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from recovery.domain.models import (
    Channel,
    Customer,
    FailureEvent,
    Language,
    PaymentMethod,
    Subscription,
)
from recovery.simulation.environment import RecoveryEnvironment

_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune",
    "Kolkata", "Ahmedabad", "Jaipur", "Kochi", "Lucknow", "Indore",
]
_CITY_LANG = {
    "Chennai": Language.TA, "Kochi": Language.TA, "Hyderabad": Language.TE,
    "Pune": Language.MR, "Kolkata": Language.BN, "Bengaluru": Language.KN,
}
_LANG_WEIGHTS = {  # baseline national mix before city override
    Language.EN: 0.30, Language.HINGLISH: 0.30, Language.HI: 0.25,
    Language.TA: 0.04, Language.TE: 0.04, Language.MR: 0.03,
    Language.KN: 0.02, Language.BN: 0.02,
}
_PLANS = [
    ("Lite", 14900), ("Basic", 29900), ("Pro", 49900),
    ("Plus", 99900), ("Business", 199900), ("Scale", 499900),
]
_METHODS = [
    (PaymentMethod.UPI_AUTOPAY, 0.42),
    (PaymentMethod.CARD, 0.34),
    (PaymentMethod.EMANDATE, 0.14),
    (PaymentMethod.NETBANKING, 0.10),
]
# Failure-reason mix on a realistic recurring book (weights need not sum to 1).
_REASON_MIX = {
    "insufficient_funds": 0.30,
    "do_not_honour": 0.18,
    "issuer_unavailable": 0.06,
    "gateway_technical_error": 0.05,
    "payment_frequency_exceeded": 0.04,
    "transaction_limit_exceeded": 0.04,
    "card_expired": 0.09,
    "card_disabled": 0.04,
    "authentication_failed": 0.06,
    "mandate_paused": 0.04,
    "mandate_revoked": 0.03,
    "international_transaction_not_allowed": 0.02,
    "payer_account_frozen": 0.015,
    "stolen_or_lost_card": 0.015,
    "invalid_card": 0.02,
}
_SALARY_DAYS = [1, 1, 1, 5, 7, 7, 10, 25, 28, 30]  # clustered like real payroll


@dataclass
class Population:
    customers: dict[str, Customer]
    subscriptions: dict[str, Subscription]
    failures: list[FailureEvent]
    seed: int

    def environment(self) -> RecoveryEnvironment:
        env = RecoveryEnvironment(self.customers, self.subscriptions, seed=self.seed)
        env.register_failures(self.failures)
        return env

    # -- persistence --------------------------------------------------------- #
    def save(self, path: str | Path) -> None:
        payload = {
            "seed": self.seed,
            "customers": [c.model_dump(mode="json") for c in self.customers.values()],
            "subscriptions": [s.model_dump(mode="json") for s in self.subscriptions.values()],
            "failures": [f.model_dump(mode="json") for f in self.failures],
        }
        Path(path).write_text(json.dumps(payload))

    @classmethod
    def load(cls, path: str | Path) -> Population:
        payload = json.loads(Path(path).read_text())
        customers = {c["id"]: Customer(**c) for c in payload["customers"]}
        subscriptions = {s["id"]: Subscription(**s) for s in payload["subscriptions"]}
        failures = [FailureEvent(**f) for f in payload["failures"]]
        return cls(
            customers=customers,
            subscriptions=subscriptions,
            failures=failures,
            seed=payload["seed"],
        )


def _weighted(rng: np.random.Generator, options: list, weights: list[float]):
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    return options[int(rng.choice(len(options), p=w))]


def _make_customer(rng: np.random.Generator, i: int) -> Customer:
    city = str(rng.choice(_CITIES))
    if city in _CITY_LANG and rng.random() < 0.6:
        language = _CITY_LANG[city]
    else:
        language = _weighted(rng, list(_LANG_WEIGHTS), list(_LANG_WEIGHTS.values()))
    tenure = int(np.clip(rng.exponential(10) + 1, 1, 96))
    # Engagement is a HIDDEN latent (never fed to the models). We correlate it
    # mildly with tenure so that the observable tenure carries a real — but noisy —
    # signal the models can learn from, mirroring "loyal customers pay once nudged".
    tenure_signal = 1.0 / (1.0 + np.exp(-(tenure - 12) / 12.0))
    engagement = float(np.clip(0.7 * rng.beta(2.4, 2.0) + 0.3 * tenure_signal, 0.03, 0.98))
    channel = _weighted(
        rng,
        [Channel.WHATSAPP, Channel.EMAIL, Channel.SMS, Channel.IN_APP],
        [0.55, 0.22, 0.13, 0.10],
    )
    return Customer(
        id=f"cust_{i:05d}",
        name=f"Customer {i:05d}",
        email=f"user{i:05d}@example.in",
        phone=f"+9198{rng.integers(10_000_000, 99_999_999)}",
        city=city,
        language=language,
        preferred_channel=channel,
        tenure_months=tenure,
        salary_day=int(rng.choice(_SALARY_DAYS)),
        engagement=engagement,
        lifetime_value_paise=0,  # filled after subscription is known
    )


def generate_population(
    n_customers: int = 4000,
    n_failures: int = 12000,
    seed: int = 7,
    horizon_days: int = 120,
) -> Population:
    """Build a reproducible population and a stream of failed recurring charges."""
    rng = np.random.default_rng(seed)
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)

    customers: dict[str, Customer] = {}
    subscriptions: dict[str, Subscription] = {}
    cust_ids: list[str] = []

    for i in range(n_customers):
        cust = _make_customer(rng, i)
        plan_name, amount = _PLANS[int(rng.choice(len(_PLANS)))]
        method = _weighted(rng, [m for m, _ in _METHODS], [w for _, w in _METHODS])
        sub = Subscription(
            id=f"sub_{i:05d}",
            customer_id=cust.id,
            plan_name=plan_name,
            amount_paise=amount,
            method=method,
            mandate_max_paise=amount * 5,
            created_at=now - timedelta(days=int(cust.tenure_months * 30)),
        )
        cust.lifetime_value_paise = amount * cust.tenure_months
        customers[cust.id] = cust
        subscriptions[sub.id] = sub
        cust_ids.append(cust.id)

    reason_codes = list(_REASON_MIX)
    reason_weights = np.asarray(list(_REASON_MIX.values()))
    reason_weights = reason_weights / reason_weights.sum()

    # Some customers are "repeat offenders" — draw failures with a mild power bias.
    pick_weights = rng.pareto(3.0, size=n_customers) + 1.0
    pick_weights /= pick_weights.sum()

    failures: list[FailureEvent] = []
    for k in range(n_failures):
        cust_id = cust_ids[int(rng.choice(n_customers, p=pick_weights))]
        sub = subscriptions[f"sub_{cust_id.split('_')[1]}"]
        reason = reason_codes[int(rng.choice(len(reason_codes), p=reason_weights))]
        days_ago = int(rng.integers(0, horizon_days))
        # recurring debits usually attempt near the billing day; add hour jitter
        occurred = now - timedelta(
            days=days_ago, hours=int(rng.integers(0, 24)), minutes=int(rng.integers(0, 60))
        )
        # attempt number: mostly first attempt, sometimes a later retry landed here
        attempt = int(rng.choice([1, 1, 1, 2, 3], p=[0.5, 0.2, 0.15, 0.1, 0.05]))
        failures.append(
            FailureEvent(
                id=f"fail_{k:06d}",
                subscription_id=sub.id,
                customer_id=cust_id,
                occurred_at=occurred,
                amount_paise=sub.amount_paise,
                method=sub.method,
                reason_code=reason,
                attempt_number=attempt,
                razorpay_payment_id=f"pay_TEST{k:06d}",
                razorpay_order_id=f"order_TEST{k:06d}",
            )
        )

    return Population(
        customers=customers,
        subscriptions=subscriptions,
        failures=failures,
        seed=seed,
    )
