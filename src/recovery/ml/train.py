"""Train and evaluate the recovery + timing models from the observational logs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from recovery.ml.models import RecoveryModel, TimingModel, _DictGBM

# Columns present in the CSVs that are labels/metadata/group-keys, not model features.
_CASE_NON_FEATURES = {
    "label", "attempts", "days_to_recover", "failure_id", "customer_id", "amount_paise"
}
_TIMING_NON_FEATURES = {"label", "failure_id"}


def _rows_and_labels(df: pd.DataFrame, non_features: set[str]) -> tuple[list[dict], np.ndarray]:
    feature_cols = [c for c in df.columns if c not in non_features]
    rows = df[feature_cols].to_dict("records")
    y = df["label"].to_numpy().astype(int)
    return rows, y


def _fit_and_score(
    rows: list[dict], y: np.ndarray, seed: int, groups: np.ndarray | None = None
) -> tuple[_DictGBM, dict]:
    # GROUPED split: probes of the same failure / failures of the same customer must
    # not straddle train and val, or the validation metric is inflated by near-dupes.
    idx = np.arange(len(y))
    if groups is None:
        groups = idx
    tr, va = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(idx, y, groups)
    )
    core = _DictGBM(random_state=seed)
    core.fit([rows[i] for i in tr], y[tr])
    p_va = core.proba([rows[i] for i in va])
    val_labels = y[va]
    metrics = {
        "n_train": int(len(tr)),
        "n_val": int(len(va)),
        "n_groups": int(len(np.unique(groups))),
        "positive_rate": float(y.mean()),
        "roc_auc": (
            float(roc_auc_score(val_labels, p_va)) if len(set(val_labels)) > 1 else float("nan")
        ),
        "avg_precision": float(average_precision_score(val_labels, p_va)),
    }
    # Refit on the full data for the shipped artifact.
    core_full = _DictGBM(random_state=seed)
    core_full.fit(rows, y)
    return core_full, metrics


def train_recovery_model(cases: pd.DataFrame, seed: int = 7) -> tuple[RecoveryModel, dict]:
    rows, y = _rows_and_labels(cases, _CASE_NON_FEATURES)
    groups = (
        cases["customer_id"].to_numpy() if "customer_id" in cases.columns else None
    )
    core, metrics = _fit_and_score(rows, y, seed, groups=groups)
    return RecoveryModel.from_core(core), metrics


def train_timing_model(timing: pd.DataFrame, seed: int = 7) -> tuple[TimingModel, dict]:
    rows, y = _rows_and_labels(timing, _TIMING_NON_FEATURES)
    groups = (
        timing["failure_id"].to_numpy() if "failure_id" in timing.columns else None
    )
    core, metrics = _fit_and_score(rows, y, seed, groups=groups)
    return TimingModel(core), metrics


def train_all(data_dir: str | Path, model_dir: str | Path, seed: int = 7) -> dict:
    data_dir, model_dir = Path(data_dir), Path(model_dir)
    cases = pd.read_csv(data_dir / "train_cases.csv")
    timing = pd.read_csv(data_dir / "train_timing.csv")

    recovery_model, rec_metrics = train_recovery_model(cases, seed)
    timing_model, tim_metrics = train_timing_model(timing, seed)

    recovery_model.save(model_dir)
    timing_model.save(model_dir)

    return {"recovery": rec_metrics, "timing": tim_metrics}
