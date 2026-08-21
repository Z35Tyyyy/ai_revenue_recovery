"""Executor that performs recovery actions for real against Razorpay test mode.

Unlike the simulated executor, real recovery success is confirmed *asynchronously*
by a ``payment.captured`` webhook — you can't know synchronously whether a customer
paid. So this executor reports *dispatch* success (a real Payment Link was created,
a retry was scheduled) and leaves final confirmation to the webhook pipeline. It is
used by the live demo and the API's manual-action endpoint, not by the batch
evaluation (which needs synchronous ground truth).
"""

from __future__ import annotations

from datetime import datetime

from recovery.domain.models import RecoveryAction, RecoveryCase, format_inr
from recovery.llm.dunning import DunningMessage
from recovery.policy.executor import ExecutionResult
from recovery.razorpay.client import Gateway, PaymentLink, get_gateway


class RazorpayExecutor:
    def __init__(self, gateway: Gateway | None = None) -> None:
        self.gateway = gateway or get_gateway()

    @property
    def live(self) -> bool:
        return self.gateway.live

    def create_recovery_link(self, case: RecoveryCase) -> PaymentLink:
        desc = (
            f"Recover {format_inr(case.failure.amount_paise)} for "
            f"{case.subscription.plan_name} (case {case.id})"
        )
        return self.gateway.create_payment_link(case, desc)

    def retry(
        self, case: RecoveryCase, at: datetime, attempt_number: int
    ) -> ExecutionResult:
        # Test mode cannot auto-charge a saved instrument without a live mandate, so a
        # retry is *scheduled*; the payment.captured/failed webhook confirms the result.
        return ExecutionResult(
            succeeded=False,
            detail=f"retry scheduled for {at:%d %b %H:%M} (confirmed via webhook)",
            meta={"scheduled_at": at.isoformat(), "attempt_number": attempt_number},
        )

    def nudge(
        self, case: RecoveryCase, action: RecoveryAction, message: DunningMessage
    ) -> ExecutionResult:
        link = self.create_recovery_link(case)
        return ExecutionResult(
            succeeded=False,  # awaiting customer payment (webhook will confirm)
            detail=f"{'real' if link.is_mock is False else 'mock'} payment link created",
            payment_link=link.short_url,
            meta={"payment_link_id": link.id, "is_mock": link.is_mock},
        )
