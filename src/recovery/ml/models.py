"""The two learned models behind the engine.

* :class:`RecoveryModel` — P(this failed charge is eventually recoverable). Used to
  triage effort and to decide when to *stop* spending on a dead case.
* :class:`TimingModel` — P(a retry at a given slot succeeds). Scanning it over the
  next fortnight yields the optimal retry moment per customer — our self-hosted,
  explainable take on "smart retries".

Both are gradient-boosted trees over a :class:`DictVectorizer`, so the exact dict
produced by :mod:`recovery.ml.features` at serve time matches training with no
skew. Models serialise to a single ``.joblib`` (vectoriser + estimator together).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer

from recovery.domain.models import Customer, FailureEvent, Subscription
from recovery.ml.features import case_feature_row, timing_feature_row

# Candidate retry hours scanned by the timing model (payday-morning, evening, and
# the classic just-after-midnight auto-debit window).
CANDIDATE_HOURS: tuple[int, ...] = (0, 1, 9, 10, 11, 13, 15, 18, 19, 21)
_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class _DictGBM:
    """DictVectorizer + HistGradientBoostingClassifier bundled for serving."""

    def __init__(self, **gbm_kwargs) -> None:
        self.vec = DictVectorizer(sparse=False)
        params = dict(
            max_depth=None,
            learning_rate=0.08,
            max_iter=300,
            l2_regularization=1.0,
            early_stopping=True,
            validation_fraction=0.12,
            random_state=7,
        )
        params.update(gbm_kwargs)
        self.clf = HistGradientBoostingClassifier(**params)

    def fit(self, rows: list[dict], y: np.ndarray) -> _DictGBM:
        X = self.vec.fit_transform(rows)
        self.clf.fit(X, y)
        return self

    def proba(self, rows: list[dict]) -> np.ndarray:
        X = self.vec.transform(rows)
        return self.clf.predict_proba(X)[:, 1]

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: str | Path) -> _DictGBM:
        return joblib.load(path)


# --------------------------------------------------------------------------- #
# Recovery-probability (triage) model
# --------------------------------------------------------------------------- #
class RecoveryModel:
    filename = "recovery_model.joblib"

    def __init__(self, core: _DictGBM) -> None:
        self.core = core

    @classmethod
    def from_core(cls, core: _DictGBM) -> RecoveryModel:
        return cls(core)

    def predict_case(
        self, failure: FailureEvent, customer: Customer, subscription: Subscription
    ) -> float:
        row = case_feature_row(failure, customer, subscription)
        return float(self.core.proba([row])[0])

    def predict_rows(self, rows: list[dict]) -> np.ndarray:
        return self.core.proba(rows)

    def save(self, model_dir: str | Path) -> None:
        self.core.save(Path(model_dir) / self.filename)

    @classmethod
    def load(cls, model_dir: str | Path) -> RecoveryModel:
        return cls(_DictGBM.load(Path(model_dir) / cls.filename))


# --------------------------------------------------------------------------- #
# Optimal-timing model
# --------------------------------------------------------------------------- #
@dataclass
class SlotScore:
    when: datetime
    prob: float

    @property
    def label(self) -> str:
        return f"{_DAY_NAMES[self.when.weekday()]} {self.when:%d %b %H:%M}"


class TimingModel:
    filename = "timing_model.joblib"

    def __init__(self, core: _DictGBM) -> None:
        self.core = core

    def score_slot(
        self,
        failure: FailureEvent,
        customer: Customer,
        subscription: Subscription,
        at: datetime,
        attempt_number: int,
    ) -> float:
        row = timing_feature_row(failure, customer, subscription, at, attempt_number)
        return float(self.core.proba([row])[0])

    def rank_slots(
        self,
        failure: FailureEvent,
        customer: Customer,
        subscription: Subscription,
        from_time: datetime,
        attempt_number: int,
        horizon_days: int = 14,
        candidate_hours: tuple[int, ...] = CANDIDATE_HOURS,
    ) -> list[SlotScore]:
        """Score every (day, hour) slot in the horizon and return them best-first."""
        base = from_time.replace(minute=0, second=0, microsecond=0)
        slots: list[datetime] = []
        for d in range(1, horizon_days + 1):
            day = base + timedelta(days=d)
            for h in candidate_hours:
                slots.append(day.replace(hour=h))
        rows = [
            timing_feature_row(failure, customer, subscription, s, attempt_number)
            for s in slots
        ]
        probs = self.core.proba(rows)
        ranked = sorted(
            (SlotScore(when=s, prob=float(p)) for s, p in zip(slots, probs, strict=True)),
            key=lambda x: x.prob,
            reverse=True,
        )
        return ranked

    def best_slot(
        self,
        failure: FailureEvent,
        customer: Customer,
        subscription: Subscription,
        from_time: datetime,
        attempt_number: int,
        horizon_days: int = 14,
    ) -> SlotScore:
        return self.rank_slots(
            failure, customer, subscription, from_time, attempt_number, horizon_days
        )[0]

    def save(self, model_dir: str | Path) -> None:
        self.core.save(Path(model_dir) / self.filename)

    @classmethod
    def load(cls, model_dir: str | Path) -> TimingModel:
        return cls(_DictGBM.load(Path(model_dir) / cls.filename))
