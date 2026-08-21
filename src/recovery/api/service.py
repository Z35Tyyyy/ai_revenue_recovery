"""Application service: loads models once, runs a sample of recovery episodes to
warm the bandit and produce a live case stream, and answers the API's queries.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from recovery.api.schemas import PlanRequest
from recovery.config import Settings, get_settings
from recovery.domain.models import (
    Customer,
    FailureEvent,
    RecoveryCase,
    Subscription,
    format_inr,
)
from recovery.eval.executor import SimulatedExecutor
from recovery.eval.harness import build_case
from recovery.llm.dunning import DunningGenerator
from recovery.ml.models import RecoveryModel, TimingModel
from recovery.policy.bandit import ContextualBandit
from recovery.policy.engine import Decision, RecoveryEngine
from recovery.razorpay.client import get_gateway
from recovery.razorpay.executor import RazorpayExecutor
from recovery.razorpay.webhooks import parse_failure_event, verify_webhook_signature
from recovery.simulation.generator import Population, generate_population


def _action_dict(a) -> dict:
    return {
        "type": a.type.value,
        "channel": a.channel.value,
        "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
        "predicted_success": a.predicted_success,
        "succeeded": a.succeeded,
        "authored_by": a.meta.get("authored_by"),
    }


def case_record(case: RecoveryCase, decision: Decision | None = None) -> dict:
    c = case.customer
    first_action = case.actions[0] if case.actions else None
    return {
        "id": case.id,
        "reason": case.failure.reason_code,
        "class": case.recoverability_class.value,
        "amount_paise": case.failure.amount_paise,
        "amount": format_inr(case.failure.amount_paise),
        "method": case.failure.method.value,
        "occurred_at": case.failure.occurred_at.isoformat(),
        "customer": {
            "id": c.id,
            "city": c.city,
            "language": c.language.value,
            "channel": c.preferred_channel.value,
            "tenure_months": c.tenure_months,
            "salary_day": c.salary_day,
        },
        "status": case.status.value,
        "recovered": case.status.value == "recovered",
        "predicted_recover_prob": round(case.predicted_recover_prob or 0.0, 3),
        "predicted_best_slot": case.predicted_best_slot,
        "recovered_amount": format_inr(case.recovered_amount_paise),
        "decision": (
            {
                "action": decision.action_type.value,
                "prob": round(decision.prob, 3),
                "ev_paise": int(decision.ev_paise),
                "when": decision.when.isoformat() if decision.when else None,
            }
            if decision
            else (
                {
                    "action": first_action.type.value,
                    "prob": round(first_action.predicted_success or 0.0, 3),
                    "ev_paise": None,
                    "when": first_action.scheduled_at.isoformat()
                    if first_action.scheduled_at
                    else None,
                }
                if first_action
                else None
            )
        ),
        "candidates": (
            [
                {
                    "action": cand.action_type.value,
                    "prob": round(cand.prob, 3),
                    "ev_paise": int(cand.ev_paise),
                    "label": cand.label,
                }
                for cand in decision.candidates
            ]
            if decision
            else []
        ),
        "actions": [_action_dict(a) for a in case.actions],
        "trace": case.trace,
    }


class RecoveryService:
    def __init__(
        self,
        settings: Settings | None = None,
        sample_size: int = 600,
        recovery_model: RecoveryModel | None = None,
        timing_model: TimingModel | None = None,
        population: Population | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.recovery_model = recovery_model or RecoveryModel.load(self.settings.model_dir)
        self.timing_model = timing_model or TimingModel.load(self.settings.model_dir)
        self.population = population or self._load_population()
        self.dunning = DunningGenerator()
        self.gateway = get_gateway(self.settings)
        self.bandit = ContextualBandit(seed=self.settings.seed)
        self.engine = RecoveryEngine(
            self.recovery_model, self.timing_model, dunning=self.dunning, bandit=self.bandit
        )
        self._records: list[dict] = []
        self._warm(sample_size)
        self._holdout = self._load_holdout()

    # -- startup ------------------------------------------------------------- #
    def _load_population(self) -> Population:
        path = self.settings.data_dir / "population.json"
        if path.exists():
            return Population.load(path)
        return generate_population(n_customers=1000, n_failures=3000, seed=self.settings.seed)

    def _load_holdout(self) -> dict | None:
        path = self.settings.report_dir / "eval.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return None
        return None

    def _warm(self, sample_size: int) -> None:
        env = self.population.environment()
        executor = SimulatedExecutor(env)
        sample = self.population.failures[:sample_size]
        for f in sample:
            case = build_case(f, self.population.customers, self.population.subscriptions)
            self.engine.run_episode(case, executor)
            self._records.append(case_record(case))

    # -- queries ------------------------------------------------------------- #
    def health(self) -> dict:
        return {
            "status": "ok",
            "razorpay_live": self.gateway.live,
            "llm_enabled": self.settings.llm_enabled,
            "models_loaded": True,
            "sample_cases": len(self._records),
            "has_holdout_eval": self._holdout is not None,
        }

    def metrics(self) -> dict:
        total = len(self._records)
        recovered = sum(1 for r in self._records if r["recovered"])
        rev_total = sum(r["amount_paise"] for r in self._records)
        rev_rec = sum(r["amount_paise"] for r in self._records if r["recovered"])
        by_class: dict[str, list[int]] = {}
        by_reason: dict[str, int] = {}
        for r in self._records:
            bc = by_class.setdefault(r["class"], [0, 0])
            bc[1] += 1
            bc[0] += int(r["recovered"])
            by_reason[r["reason"]] = by_reason.get(r["reason"], 0) + 1
        return {
            "holdout": self._holdout,
            "live_sample": {
                "total": total,
                "recovered": recovered,
                "recovery_rate": round(recovered / total, 4) if total else 0.0,
                "revenue_recovered_paise": rev_rec,
                "revenue_total_paise": rev_total,
                "by_class_rate": {
                    k: round(v[0] / v[1], 3) for k, v in sorted(by_class.items()) if v[1]
                },
                "by_reason_count": dict(sorted(by_reason.items(), key=lambda x: -x[1])),
            },
            "bandit": self.bandit.snapshot(),
            "capabilities": {
                "razorpay_live": self.gateway.live,
                "llm_enabled": self.settings.llm_enabled,
            },
        }

    def cases(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        reason: str | None = None,
        klass: str | None = None,
    ) -> dict:
        rows = self._records
        if status:
            rows = [r for r in rows if r["status"] == status]
        if reason:
            rows = [r for r in rows if r["reason"] == reason]
        if klass:
            rows = [r for r in rows if r["class"] == klass]
        total = len(rows)
        return {"total": total, "cases": rows[offset : offset + limit]}

    def plan(self, req: PlanRequest) -> dict:
        now = datetime.now(timezone.utc)
        customer = Customer(
            id="cust_interactive",
            name=req.customer_name,
            email=req.customer_email,
            phone=req.customer_phone,
            city=req.city,
            language=req.language,
            preferred_channel=req.preferred_channel,
            tenure_months=req.tenure_months,
            salary_day=req.salary_day,
            lifetime_value_paise=req.amount_paise * max(1, req.tenure_months),
        )
        subscription = Subscription(
            id="sub_interactive",
            customer_id=customer.id,
            plan_name=req.plan_name,
            amount_paise=req.amount_paise,
            method=req.method,
        )
        failure = FailureEvent(
            id=f"fail_interactive_{int(now.timestamp())}",
            subscription_id=subscription.id,
            customer_id=customer.id,
            occurred_at=now,
            amount_paise=req.amount_paise,
            method=req.method,
            reason_code=req.reason_code,
            attempt_number=req.attempt_number,
        )
        case = RecoveryCase(
            id=failure.id, failure=failure, customer=customer, subscription=subscription
        )
        decision = self.engine.plan(case)

        payment_link = None
        message = None
        if req.create_payment_link:
            executor = RazorpayExecutor(self.gateway)
            link = executor.create_recovery_link(case)
            msg = self.dunning.generate(
                case, req.preferred_channel, req.language, link.short_url
            )
            payment_link = {
                "id": link.id,
                "short_url": link.short_url,
                "is_mock": link.is_mock,
                "amount": format_inr(link.amount_paise),
            }
            message = {
                "text": msg.text,
                "language": msg.language.value,
                "channel": msg.channel.value,
                "authored_by": msg.authored_by,
                "subject": msg.subject,
            }

        record = case_record(case, decision)
        record["payment_link"] = payment_link
        record["message"] = message
        return record

    def handle_webhook(self, raw_body: bytes, signature: str | None) -> dict:
        secret = self.settings.razorpay_webhook_secret
        verified = False
        if secret:
            verified = verify_webhook_signature(raw_body, signature or "", secret)
            if not verified:
                return {"ok": False, "error": "invalid signature"}
        try:
            event = json.loads(raw_body.decode() or "{}")
        except Exception:
            return {"ok": False, "error": "invalid json"}

        failure = parse_failure_event(event)
        if failure is None:
            return {"ok": True, "handled": False, "reason": "event not actionable"}

        customer = self.population.customers.get(
            failure.customer_id,
            Customer(id=failure.customer_id, salary_day=1, tenure_months=6),
        )
        subscription = self.population.subscriptions.get(
            failure.subscription_id,
            Subscription(
                id=failure.subscription_id,
                customer_id=customer.id,
                amount_paise=failure.amount_paise or 49900,
            ),
        )
        case = RecoveryCase(
            id=f"case_{failure.id}", failure=failure, customer=customer, subscription=subscription
        )
        decision = self.engine.plan(case)
        return {
            "ok": True,
            "handled": True,
            "signature_verified": verified,
            "case": case_record(case, decision),
        }


_service: RecoveryService | None = None


def get_service() -> RecoveryService:
    global _service
    if _service is None:
        _service = RecoveryService()
    return _service
