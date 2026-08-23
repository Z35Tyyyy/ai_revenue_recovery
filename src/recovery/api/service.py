"""Application service: loads models once, runs a sample of recovery episodes to
warm the bandit and produce a live case stream, and answers the API's queries.
"""

from __future__ import annotations

import json
import logging
import random
from collections import OrderedDict
from datetime import datetime, timezone

from recovery.api.schemas import PlanRequest
from recovery.config import Settings, get_settings
from recovery.domain.models import (
    ActionType,
    Customer,
    FailureEvent,
    RecoverabilityClass,
    RecoveryCase,
    Subscription,
    format_inr,
)
from recovery.domain.taxonomy import classify_reason
from recovery.eval.executor import SimulatedExecutor
from recovery.eval.harness import build_case
from recovery.llm.dunning import DunningGenerator
from recovery.llm.reasoning import ReasoningGenerator
from recovery.ml.models import RecoveryModel, TimingModel
from recovery.policy.bandit import ContextualBandit
from recovery.policy.engine import Decision, RecoveryEngine
from recovery.razorpay.client import MockGateway, get_gateway
from recovery.razorpay.executor import RazorpayExecutor
from recovery.razorpay.webhooks import (
    is_recovery_confirmation,
    parse_failure_event,
    verify_webhook_signature,
)
from recovery.scheduler import RetryScheduler
from recovery.simulation.generator import Population, generate_population
from recovery.store import RecoveryStore

logger = logging.getLogger("recovery.api")


def _action_dict(a) -> dict:
    return {
        "type": a.type.value,
        "channel": a.channel.value,
        "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
        "predicted_success": a.predicted_success,
        "succeeded": a.succeeded,
        "authored_by": a.meta.get("authored_by"),
        "message": a.message,
        "payment_link": a.payment_link,
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
        # Live generator (used for the interactive /api/plan demo); the warm-up
        # engine forces templates so startup stays fast and offline.
        self.dunning = DunningGenerator()
        self._template_dunning = DunningGenerator(force_templates=True)  # chaos/LLM fallback
        # LLM reasoning layer: explains (never makes) the engine's decision.
        self.reasoning = ReasoningGenerator()
        self._template_reasoning = ReasoningGenerator(force_templates=True)
        # Chaos switches — deliberately fail a dependency to demo graceful fallbacks.
        self._chaos = {"llm": False, "gateway": False}
        self.gateway = get_gateway(self.settings)
        self.bandit = ContextualBandit(seed=self.settings.seed)
        # Durable store: reload the bandit's learned posteriors so learning survives
        # restarts (the "Measure feeds back ↺" loop is only real if it persists).
        self.store = RecoveryStore(self.settings.db_path)
        saved = self.store.load_bandit()
        if saved:
            self.bandit.restore_ab(saved)
        self.scheduler = RetryScheduler(self.store)
        self._rng = random.Random(self.settings.seed)  # noqa: S311 (demo confirmations)
        self.engine = RecoveryEngine(
            self.recovery_model,
            self.timing_model,
            dunning=DunningGenerator(force_templates=True),
            bandit=self.bandit,
        )
        self._records: list[dict] = []
        # Bounded set of processed webhook event ids (idempotency / replay guard).
        self._seen_events: OrderedDict[str, bool] = OrderedDict()
        self._warm(sample_size)
        self.store.save_bandit(self.bandit.export_ab())  # persist what warm-up learned
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
            "llm_provider": self.settings.llm_provider if self.settings.llm_enabled else None,
            "models_loaded": True,
            "sample_cases": len(self._records),
            "persisted_cases": self.store.count_cases(),
            "recovered_cases": self.store.recovered_count(),
            "pending_jobs": self.store.pending_job_count(),
            "chaos": dict(self._chaos),
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
            "real_recoveries": self.real_recovery_proof(),
            "capabilities": {
                "razorpay_live": self.gateway.live,
                "llm_enabled": self.settings.llm_enabled,
                "llm_provider": self.settings.llm_provider if self.settings.llm_enabled else None,
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
            id=f"fail_interactive_{int(now.timestamp() * 1_000_000)}",
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
        link_note = None
        resilience = None
        if req.create_payment_link:
            chaos = self._chaos
            notes: list[str] = []
            # Gateway: chaos forces the real gateway "down" so the mock fallback shows.
            if chaos["gateway"]:
                desc = (
                    f"Recover {format_inr(case.failure.amount_paise)} for "
                    f"{case.subscription.plan_name} (case {case.id})"
                )
                link = MockGateway().create_payment_link(case, desc)
                notes.append("Gateway forced DOWN → deterministic mock link used ✓")
            else:
                link = self._create_link_resilient(case)
            link_url = link.short_url if link else ""
            if link is not None:
                payment_link = {
                    "id": link.id,
                    "short_url": link.short_url,
                    "is_mock": link.is_mock,
                    "amount": format_inr(link.amount_paise),
                    "status": link.status,
                }
                if link.is_mock and self.gateway.live and not chaos["gateway"]:
                    link_note = "Razorpay was unreachable — showing a mock link."
            # LLM: chaos forces the template writer so a model outage still recovers.
            dgen = self._template_dunning if chaos["llm"] else self.dunning
            if chaos["llm"]:
                notes.append("LLM forced DOWN → deterministic template message used ✓")
            try:
                msg = dgen.generate(case, req.preferred_channel, req.language, link_url)
                message = {
                    "text": msg.text,
                    "language": msg.language.value,
                    "channel": msg.channel.value,
                    "authored_by": msg.authored_by,
                    "subject": msg.subject,
                }
            except Exception:
                logger.warning("dunning generation failed", exc_info=True)
            if chaos["llm"] or chaos["gateway"]:
                resilience = {
                    "llm_down": chaos["llm"],
                    "gateway_down": chaos["gateway"],
                    "notes": notes,
                }

        record = case_record(case, decision)
        record["payment_link"] = payment_link
        record["message"] = message
        if link_note:
            record["link_note"] = link_note
        if resilience:
            record["resilience"] = resilience
        # Durable + real: schedule the decided action (compliance-checked) and persist.
        schedule = None
        if decision and decision.action_type != ActionType.GIVE_UP:
            schedule = self.scheduler.schedule(
                case.id,
                decision.action_type,
                req.method,
                req.amount_paise,
                decision.channel,
                decision.when,
                now,
            )
            record["schedule"] = schedule

        # Agentic layer: an LLM rationale for the decision, plus the tool-call timeline
        # the agent actually ran. The ML/bandit MAKES the call; the LLM explains it.
        chosen, runner_up = self._reasoning_context(decision)
        compliance_note = self._compliance_note(schedule)
        rgen = self._template_reasoning if self._chaos["llm"] else self.reasoning
        reasoning = rgen.generate(case, chosen, runner_up, compliance_note)
        record["reasoning"] = {"text": reasoning.text, "authored_by": reasoning.authored_by}
        record["tools"] = self._build_tools(case, decision, schedule, payment_link, message)

        self.store.save_case(record)
        return record

    @staticmethod
    def _reasoning_context(decision) -> tuple[dict, dict | None]:
        chosen = {
            "action": decision.action_type.value,
            "prob": decision.prob,
            "ev_paise": decision.ev_paise,
        }
        runner_up = None
        for cand in getattr(decision, "candidates", None) or []:
            if cand.action_type.value != chosen["action"]:
                runner_up = {
                    "action": cand.action_type.value,
                    "prob": cand.prob,
                    "ev_paise": cand.ev_paise,
                }
                break
        return chosen, runner_up

    @staticmethod
    def _compliance_note(schedule: dict | None) -> str | None:
        if not schedule:
            return None
        if schedule.get("notes"):
            return "; ".join(schedule["notes"])
        if schedule.get("requires_afa"):
            return "Above the ₹15,000 AFA cap — needs additional-factor authentication."
        if schedule.get("allowed"):
            return "Within RBI limits (24h pre-debit notice, ₹15k AFA cap)."
        return schedule.get("reason")

    def _build_tools(
        self, case, decision, schedule: dict | None, payment_link, message
    ) -> list[dict]:
        """The agent's tool-call timeline — each output is a real value from this run."""
        reason = classify_reason(case.failure.reason_code)
        slot = case.predicted_best_slot
        tools = [
            {
                "tool": "diagnose_failure",
                "input": case.failure.reason_code,
                "output": (
                    f"{case.recoverability_class.value} · "
                    f"retry {'helps' if reason.retry_helps else 'is futile'}"
                ),
                "ok": True,
            },
            {
                "tool": "predict_recovery_probability",
                "input": "ML · gradient-boosted",
                "output": f"{round((case.predicted_recover_prob or 0) * 100)}% base prob",
                "ok": True,
            },
            {
                "tool": "predict_optimal_time",
                "input": "ML · timing model",
                "output": (f"best slot: {slot}" if slot else "now"),
                "ok": True,
            },
            {
                "tool": "score_actions",
                "input": f"{len(getattr(decision, 'candidates', None) or [])} candidates",
                "output": (
                    f"best: {decision.action_type.value} "
                    f"(EV {format_inr(int(decision.ev_paise or 0))})"
                ),
                "ok": True,
            },
            {
                "tool": "consult_bandit",
                "input": f"class={case.recoverability_class.value}",
                "output": "Thompson-sampled posterior applied",
                "ok": True,
            },
        ]
        if schedule is not None:
            comp = (
                "allowed"
                if schedule.get("allowed")
                else ("needs AFA" if schedule.get("requires_afa") else "blocked")
            )
            tools.append(
                {
                    "tool": "check_compliance",
                    "input": "RBI 24h notice · ₹15k AFA · DLT",
                    "output": comp,
                    "ok": bool(schedule.get("allowed")),
                }
            )
        if payment_link:
            tools.append(
                {
                    "tool": "create_payment_link",
                    "input": f"Razorpay {'mock' if payment_link.get('is_mock') else 'test-mode'}",
                    "output": payment_link.get("id") or "created",
                    "ok": True,
                }
            )
        if message:
            tools.append(
                {
                    "tool": "author_message",
                    "input": f"{message.get('channel')} · {message.get('language')}",
                    "output": f"authored by {message.get('authored_by')}",
                    "ok": True,
                }
            )
        if schedule is not None and schedule.get("allowed"):
            tools.append(
                {
                    "tool": "schedule_execution",
                    "input": "durable job",
                    "output": f"job #{schedule.get('job_id')}",
                    "ok": True,
                }
            )
        return tools

    def _create_link_resilient(self, case: RecoveryCase):
        """Create a payment link without ever raising. Retries once on a transient
        gateway error, then falls back to a deterministic mock link — a Razorpay
        hiccup must not fail the whole plan (previously surfaced as a 500)."""
        executor = RazorpayExecutor(self.gateway)
        for attempt in range(2):
            try:
                return executor.create_recovery_link(case)
            except Exception:
                logger.warning(
                    "payment link creation failed (attempt %d/2)", attempt + 1, exc_info=True
                )
        try:
            desc = (
                f"Recover {format_inr(case.failure.amount_paise)} for "
                f"{case.subscription.plan_name} (case {case.id})"
            )
            return MockGateway().create_payment_link(case, desc)
        except Exception:
            logger.warning("mock link fallback failed", exc_info=True)
            return None

    # -- closing the loop: fire scheduled jobs + confirm recoveries ----------- #
    def _update_bandit_from_record(self, rec: dict, reward: bool) -> None:
        try:
            cls = RecoverabilityClass(rec.get("class"))
            arm = ActionType((rec.get("decision") or {}).get("action"))
            self.bandit.update(cls, arm, reward)
        except Exception:
            pass  # unknown class/action — skip the learning update

    def fire_due_jobs(self, now: datetime | None = None, fire_all: bool = False) -> dict:
        """Execute scheduled jobs whose time has come (or all pending, for a demo
        fast-forward). Without a real gateway webhook we *simulate* the confirmation
        from the model's predicted success probability — closing the loop and letting
        the bandit learn from the outcome. A real payment.captured webhook overrides it."""
        now = now or datetime.now(timezone.utc)
        jobs = self.store.all_pending_jobs() if fire_all else self.store.due_jobs(now)
        fired = recovered = 0
        for job in jobs:
            rec = self.store.get_case(job["case_id"])
            if rec is None:
                self.store.mark_job(job["id"], "skipped", "case missing")
                continue
            prob = float(
                (rec.get("decision") or {}).get("prob")
                or rec.get("predicted_recover_prob")
                or 0.0
            )
            ok = self._rng.random() < prob
            self.store.set_case_recovered(rec["id"], ok, source="simulated")
            self._update_bandit_from_record(rec, ok)
            self.store.mark_job(job["id"], "recovered" if ok else "failed", None)
            fired += 1
            recovered += int(ok)
        if fired:
            self.store.save_bandit(self.bandit.export_ab())
        return {
            "fired": fired,
            "recovered": recovered,
            "pending": self.store.pending_job_count(),
        }

    def confirm_recovery(
        self, case_id: str, source: str = "webhook", payment_id: str | None = None
    ) -> bool:
        """Mark a case recovered from a real gateway event (payment.captured)."""
        rec = self.store.get_case(case_id)
        if rec is None:
            return False
        self.store.set_case_recovered(case_id, True, source=source, payment_id=payment_id)
        self._update_bandit_from_record(rec, True)
        self.store.save_bandit(self.bandit.export_ab())
        return True

    @staticmethod
    def _captured_payment_id(link: dict) -> str | None:
        for p in link.get("payments") or []:
            if p.get("status") == "captured":
                return p.get("payment_id") or p.get("id")
        return None

    def check_recoveries(self) -> dict:
        """Poll Razorpay for open cases with a REAL payment link and close any that were
        paid. Closes the loop with live Razorpay data without an inbound webhook — the
        customer pays the link, we poll, a 'paid' status confirms the recovery."""
        checked = confirmed = 0
        for rec in self.store.list_cases(limit=200):
            if rec.get("recovered"):
                continue
            pl = rec.get("payment_link") or {}
            if pl.get("is_mock") or not pl.get("id"):
                continue
            checked += 1
            try:
                link = self.gateway.fetch_payment_link(pl["id"])
            except Exception:
                logger.warning("payment-link poll failed for %s", pl.get("id"), exc_info=True)
                continue
            if link.get("status") == "paid" and self.confirm_recovery(
                rec["id"], source="razorpay_poll", payment_id=self._captured_payment_id(link)
            ):
                confirmed += 1
        return {
            "checked": checked,
            "confirmed": confirmed,
            "recovered_total": self.store.recovered_count(),
        }

    def real_recovery_proof(self) -> dict:
        """Summary of recoveries closed by a real captured Razorpay payment (not the
        simulator) — the Console surfaces this as first-hand 'not a sim' evidence."""
        recs = self.store.real_recoveries()
        total = 0
        items = []
        for rec in recs:
            pl = rec.get("payment_link") or {}
            total += int(rec.get("amount_paise") or 0)
            items.append(
                {
                    "case_id": rec.get("id"),
                    "amount": rec.get("amount"),
                    "link_id": pl.get("id"),
                    "payment_id": rec.get("payment_id"),
                    "source": rec.get("recovery_source"),
                }
            )
        return {"count": len(items), "total_paise": total, "items": items[:5]}

    def set_chaos(self, llm: bool | None = None, gateway: bool | None = None) -> dict:
        """Deliberately force a dependency 'down' to demo graceful fallbacks."""
        if llm is not None:
            self._chaos["llm"] = bool(llm)
        if gateway is not None:
            self._chaos["gateway"] = bool(gateway)
        return dict(self._chaos)

    def handle_webhook(
        self, raw_body: bytes, signature: str | None, event_id: str | None = None
    ) -> dict:
        secret = self.settings.razorpay_webhook_secret
        # Fail CLOSED: never process an unsigned payment webhook unless explicitly
        # allowed for local testing. The `status` key maps to an HTTP status code.
        if not secret:
            if not self.settings.allow_unsigned_webhooks:
                return {
                    "ok": False,
                    "error": "webhook secret not configured",
                    "status": 503,
                }
            verified = False
        else:
            if not verify_webhook_signature(raw_body, signature or "", secret):
                return {"ok": False, "error": "invalid signature", "status": 401}
            verified = True

        try:
            event = json.loads(raw_body.decode() or "{}")
        except Exception:
            return {"ok": False, "error": "invalid json", "status": 400}

        # Idempotency / replay guard — Razorpay delivers at-least-once.
        dedup_key = event_id or event.get("id") or event.get("payload", {}).get(
            "payment", {}
        ).get("entity", {}).get("id")
        if dedup_key:
            if dedup_key in self._seen_events:
                return {"ok": True, "handled": False, "reason": "duplicate event"}
            self._seen_events[dedup_key] = True
            while len(self._seen_events) > 2048:
                self._seen_events.popitem(last=False)

        # Recovery confirmation (payment.captured / subscription.charged) closes the loop.
        if is_recovery_confirmation(event):
            payload = event.get("payload", {})
            entity = payload.get("payment", {}).get("entity", {}) or payload.get(
                "subscription", {}
            ).get("entity", {})
            case_id = (entity.get("notes") or {}).get("case_id")
            confirmed = self.confirm_recovery(case_id) if case_id else False
            return {"ok": True, "handled": confirmed, "event": "recovery_confirmation"}

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
        record = case_record(case, decision)
        # Persist so inbound failures show up in the live case stream. Outward
        # actions (links/notifications) are intentionally NOT auto-dispatched here.
        self._records.insert(0, record)
        del self._records[5000:]
        return {
            "ok": True,
            "handled": True,
            "signature_verified": verified,
            "case": record,
        }


_service: RecoveryService | None = None


def get_service() -> RecoveryService:
    global _service
    if _service is None:
        _service = RecoveryService()
    return _service
