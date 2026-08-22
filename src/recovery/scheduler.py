"""A real scheduler for recovery actions.

The engine's smartest output is *when* to retry ("wait for payday"). Without a
scheduler that's just a suggestion — this executes it: it enqueues each decided
action as a durable job at its (compliance-adjusted) time, and a background tick
fires due jobs through an executor, closing the loop the webhook confirms.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone

from recovery.compliance import check_action
from recovery.domain.models import ActionType, Channel, PaymentMethod
from recovery.store import RecoveryStore

logger = logging.getLogger("recovery.scheduler")

# Callback: given a due job row, actually perform the action → (status, detail).
Resolver = Callable[[dict], tuple[str, str]]


class RetryScheduler:
    def __init__(self, store: RecoveryStore) -> None:
        self.store = store

    def schedule(
        self,
        case_id: str,
        action_type: ActionType,
        method: PaymentMethod,
        amount_paise: int,
        channel: Channel,
        when: datetime | None,
        now: datetime | None = None,
        *,
        consent: bool = True,
        messages_sent_this_week: int = 0,
    ) -> dict:
        """Compliance-check + enqueue a job. Returns the compliance outcome."""
        now = now or datetime.now(timezone.utc)
        decision = check_action(
            action_type,
            method,
            amount_paise,
            when,
            now,
            consent=consent,
            messages_sent_this_week=messages_sent_this_week,
        )
        result = {
            "allowed": decision.allowed,
            "requires_afa": decision.requires_afa,
            "reason": decision.reason,
            "notes": decision.notes,
            "job_id": None,
            "run_at": None,
        }
        if not decision.allowed:
            return result
        run_at = decision.adjusted_at or when or now
        job_id = self.store.enqueue_job(case_id, action_type.value, channel.value, run_at)
        result["job_id"] = job_id
        result["run_at"] = run_at.isoformat()
        return result

    def tick(self, now: datetime, resolve: Resolver) -> int:
        """Fire all due jobs through `resolve`. Returns how many ran."""
        due = self.store.due_jobs(now)
        for job in due:
            try:
                status, detail = resolve(job)
            except Exception as e:  # a failing job must not stall the queue
                logger.warning("job %s failed", job["id"], exc_info=True)
                status, detail = "failed", str(e)
            self.store.mark_job(job["id"], status, detail)
        return len(due)

    async def run_forever(self, resolve: Resolver, interval_seconds: float = 30.0) -> None:
        """Background loop: tick the queue on an interval until cancelled."""
        while True:
            try:
                self.tick(datetime.now(timezone.utc), resolve)
            except Exception:
                logger.warning("scheduler tick error", exc_info=True)
            await asyncio.sleep(interval_seconds)
