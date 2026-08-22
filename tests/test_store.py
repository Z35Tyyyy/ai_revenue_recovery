"""Durable store: cases, persisted bandit posteriors, scheduled jobs."""

from datetime import datetime, timedelta, timezone

from recovery.domain.models import ActionType, RecoverabilityClass
from recovery.policy.bandit import ContextualBandit
from recovery.store import RecoveryStore


def _store():
    return RecoveryStore(":memory:")


def test_case_roundtrip():
    s = _store()
    s.save_case({"id": "c1", "status": "open", "recovered": False, "reason": "x",
                 "class": "soft_decline", "amount_paise": 49900, "trace": ["a"]})
    assert s.count_cases() == 1
    got = s.list_cases()[0]
    assert got["id"] == "c1" and got["trace"] == ["a"]


def test_bandit_persistence_survives_reload():
    b = ContextualBandit(seed=1)
    ctx, arm = RecoverabilityClass.INSUFFICIENT_FUNDS, ActionType.RETRY_OPTIMAL
    for _ in range(15):
        b.update(ctx, arm, reward=True)
    learned = b.mean(ctx, arm)

    s = _store()
    s.save_bandit(b.export_ab())

    b2 = ContextualBandit(seed=1)
    b2.restore_ab(s.load_bandit())
    assert abs(b2.mean(ctx, arm) - learned) < 1e-9  # learning survived the "restart"


def test_job_queue_due_and_mark():
    s = _store()
    now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    past = s.enqueue_job("c1", "retry_optimal", "none", now - timedelta(hours=1))
    s.enqueue_job("c2", "dunning_nudge", "whatsapp", now + timedelta(days=2))  # future
    due = s.due_jobs(now)
    assert len(due) == 1 and due[0]["case_id"] == "c1"
    assert s.pending_job_count() == 2
    s.mark_job(past, "done", "recovered")
    assert s.pending_job_count() == 1
