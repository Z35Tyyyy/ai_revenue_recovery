"""The side-effect boundary.

The engine decides *what* to do; an :class:`Executor` actually does it. Two
primitives are enough to express every recovery action:

* ``retry`` — re-attempt the charge at a moment in time.
* ``nudge`` — deliver a message (dunning / card-update / switch-method / grace
  offer) that asks the customer to act, with a payment link.

Swapping the executor swaps reality: a simulated executor resolves against the
hidden environment (for eval), a Razorpay executor creates real test-mode payment
links and orders (for the live demo). The engine imports only this Protocol, never
the environment — so it can never peek at ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from recovery.domain.models import RecoveryAction, RecoveryCase
from recovery.llm.dunning import DunningMessage


@dataclass
class ExecutionResult:
    succeeded: bool
    detail: str = ""
    payment_link: str | None = None
    meta: dict = field(default_factory=dict)


class Executor(Protocol):
    def retry(
        self, case: RecoveryCase, at: datetime, attempt_number: int
    ) -> ExecutionResult: ...

    def nudge(
        self, case: RecoveryCase, action: RecoveryAction, message: DunningMessage
    ) -> ExecutionResult: ...
