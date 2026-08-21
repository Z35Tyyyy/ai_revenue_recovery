"""Executor that resolves actions against the hidden simulation environment.

This is the eval-side implementation of the :class:`~recovery.policy.executor.Executor`
Protocol. It lives in the eval package precisely because it is allowed to touch the
ground-truth environment — the engine itself never can.
"""

from __future__ import annotations

from datetime import datetime

from recovery.domain.models import RecoveryAction, RecoveryCase
from recovery.llm.dunning import DunningMessage
from recovery.policy.executor import ExecutionResult
from recovery.simulation.environment import RecoveryEnvironment


class SimulatedExecutor:
    def __init__(self, env: RecoveryEnvironment) -> None:
        self.env = env

    def retry(
        self, case: RecoveryCase, at: datetime, attempt_number: int
    ) -> ExecutionResult:
        ok = self.env.resolve_retry(case.failure.id, at, attempt_number)
        return ExecutionResult(succeeded=ok, detail=f"retry @ {at:%d %b %H:%M}")

    def nudge(
        self, case: RecoveryCase, action: RecoveryAction, message: DunningMessage
    ) -> ExecutionResult:
        attempt = len([a for a in case.actions]) + 1
        ok = self.env.resolve_dunning(
            case.failure.id,
            action.channel,
            message.language,
            message.quality,
            attempt_number=attempt,
        )
        return ExecutionResult(
            succeeded=ok,
            detail=f"{message.authored_by} msg via {action.channel.value}",
            payment_link="https://rzp.io/i/demo-recovery-link",
        )
