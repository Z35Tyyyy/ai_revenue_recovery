"""The agentic recovery orchestrator.

Per failed charge it runs a short **sequential decision episode**:

    diagnose → (predict, decide) → act → observe → repeat until recovered / give up

Each step it builds candidate actions, estimates each one's *expected recovered
rupees* (learned timing model for retries; a calibrated belief for nudges), lets
the contextual bandit correct those estimates from live outcomes, and picks the
argmax — or stops when nothing is worth the spend. Every step appends a plain-
English line to the case's trace, so any decision can be explained on stage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from recovery.domain.models import (
    ActionType,
    CaseStatus,
    Channel,
    RecoverabilityClass,
    RecoveryAction,
    RecoveryCase,
    RecoveryOutcome,
    format_inr,
)
from recovery.domain.taxonomy import classify_reason
from recovery.llm.dunning import DunningGenerator
from recovery.ml.models import CANDIDATE_HOURS, RecoveryModel, TimingModel
from recovery.policy.bandit import ContextualBandit
from recovery.policy.executor import Executor

_NUDGE_BASE = {
    RecoverabilityClass.NEEDS_CARD_UPDATE: 0.50,
    RecoverabilityClass.NEEDS_REAUTH: 0.46,
    RecoverabilityClass.INSUFFICIENT_FUNDS: 0.42,
    RecoverabilityClass.SOFT_DECLINE: 0.36,
    RecoverabilityClass.TRANSIENT: 0.30,
    RecoverabilityClass.HARD_DECLINE: 0.06,
    RecoverabilityClass.UNKNOWN: 0.33,
}
_NUDGE_ACTION = {
    RecoverabilityClass.NEEDS_CARD_UPDATE: ActionType.REQUEST_CARD_UPDATE,
    RecoverabilityClass.NEEDS_REAUTH: ActionType.DUNNING_NUDGE,
    RecoverabilityClass.HARD_DECLINE: ActionType.SWITCH_METHOD,
    RecoverabilityClass.INSUFFICIENT_FUNDS: ActionType.DUNNING_NUDGE,
    RecoverabilityClass.SOFT_DECLINE: ActionType.DUNNING_NUDGE,
    RecoverabilityClass.TRANSIENT: ActionType.DUNNING_NUDGE,
    RecoverabilityClass.UNKNOWN: ActionType.DUNNING_NUDGE,
}


@dataclass
class EngineConfig:
    max_steps: int = 4
    horizon_days: int = 14
    give_up_ev_ratio: float = 0.04    # stop if best action's EV < this fraction of amount
    delay_discount_days: float = 45.0  # rupees now are worth more than rupees later
    nudge_cost_paise: int = 200       # ~₹2 messaging cost, keeps the agent from spamming
    bandit_blend: float = 0.5         # max weight given to the bandit once it's confident
    bandit_confidence_k: float = 20.0
    expected_message_quality: float = 0.85  # belief used for EV (templates); Claude lifts it


@dataclass
class Candidate:
    action_type: ActionType
    prob: float
    ev_paise: float
    when: datetime | None
    channel: Channel
    attempt_number: int
    label: str


@dataclass
class Decision:
    action_type: ActionType
    prob: float
    ev_paise: float
    when: datetime | None
    channel: Channel
    attempt_number: int
    candidates: list[Candidate] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)


class RecoveryEngine:
    def __init__(
        self,
        recovery_model: RecoveryModel,
        timing_model: TimingModel,
        dunning: DunningGenerator | None = None,
        bandit: ContextualBandit | None = None,
        config: EngineConfig | None = None,
    ) -> None:
        self.recovery_model = recovery_model
        self.timing_model = timing_model
        self.dunning = dunning or DunningGenerator()
        self.bandit = bandit
        self.config = config or EngineConfig()

    # -- stage 1: diagnose --------------------------------------------------- #
    def diagnose(self, case: RecoveryCase) -> None:
        reason = classify_reason(case.failure.reason_code)
        case.recoverability_class = reason.recoverability
        case.predicted_recover_prob = self.recovery_model.predict_case(
            case.failure, case.customer, case.subscription
        )
        case.log(
            f"Diagnosed '{case.failure.reason_code}' → {reason.recoverability.value} "
            f"(retry {'can' if reason.retry_helps else 'cannot'} help). "
            f"Triage P(recover)={case.predicted_recover_prob:.2f}."
        )

    # -- beliefs ------------------------------------------------------------- #
    def _nudge_prob(self, case: RecoveryCase, quality: float) -> float:
        cls = case.recoverability_class
        base = _NUDGE_BASE.get(cls, 0.33)
        tenure = case.customer.tenure_months
        engagement = 0.45 + 0.5 * (1.0 / (1.0 + math.exp(-(tenure - 12) / 12.0)))
        return float(min(0.9, max(0.0, base * engagement * quality)))

    def _bandit_blend(self, cls: RecoverabilityClass, arm: ActionType) -> float:
        if self.bandit is None:
            return 0.0
        obs = self.bandit_observations(cls, arm)
        return self.config.bandit_blend * (obs / (obs + self.config.bandit_confidence_k))

    def bandit_observations(self, cls: RecoverabilityClass, arm: ActionType) -> float:
        a, b = self.bandit._params(cls, arm)  # noqa: SLF001 (same package, intentional)
        return (a - self.bandit._prior) + (b - self.bandit._prior)

    def _apply_bandit(self, cls: RecoverabilityClass, arm: ActionType, prob: float) -> float:
        w = self._bandit_blend(cls, arm)
        if w <= 0:
            return prob
        return (1 - w) * prob + w * self.bandit.sample(cls, arm)

    def _discount(self, when: datetime, t0: datetime) -> float:
        days = max(0.0, (when - t0).total_seconds() / 86400.0)
        return math.exp(-days / self.config.delay_discount_days)

    # -- stage 2+3: predict + decide ---------------------------------------- #
    def _candidates(
        self, case: RecoveryCase, now: datetime, attempt_number: int
    ) -> tuple[list[Candidate], list[str]]:
        cls = case.recoverability_class
        amount = case.failure.amount_paise
        t0 = case.failure.occurred_at
        rationale: list[str] = []
        cands: list[Candidate] = []

        f, c, s = case.failure, case.customer, case.subscription

        # --- retry at the model's best slot ---
        best = self.timing_model.best_slot(
            f, c, s, now, attempt_number=attempt_number, horizon_days=self.config.horizon_days
        )
        p_opt = self._apply_bandit(cls, ActionType.RETRY_OPTIMAL, best.prob)
        ev_opt = p_opt * amount * self._discount(best.when, t0)
        cands.append(
            Candidate(ActionType.RETRY_OPTIMAL, p_opt, ev_opt, best.when, Channel.NONE,
                      attempt_number, f"retry @ {best.label}")
        )

        # --- retry at the soonest reasonable slot ---
        soon = self._soonest_slot(now)
        p_now = self.timing_model.score_slot(f, c, s, soon, attempt_number)
        p_now = self._apply_bandit(cls, ActionType.RETRY_NOW, p_now)
        ev_now = p_now * amount * self._discount(soon, t0)
        cands.append(
            Candidate(ActionType.RETRY_NOW, p_now, ev_now, soon, Channel.NONE,
                      attempt_number, f"retry soon @ {soon:%d %b %H:%M}")
        )

        # --- nudge (dunning / card-update / switch / grace) ---
        nudge_arm = _NUDGE_ACTION.get(cls, ActionType.DUNNING_NUDGE)
        q = 1.0 if self.dunning.llm.available else self.config.expected_message_quality
        p_nudge_raw = self._nudge_prob(case, q)
        p_nudge = self._apply_bandit(cls, nudge_arm, p_nudge_raw)
        nudge_when = self._next_morning(now)
        ev_nudge = p_nudge * amount * self._discount(nudge_when, t0) - self.config.nudge_cost_paise
        cands.append(
            Candidate(nudge_arm, p_nudge, ev_nudge, nudge_when, c.preferred_channel,
                      attempt_number, f"{nudge_arm.value} via {c.preferred_channel.value}")
        )

        # --- give up (always available) ---
        cands.append(
            Candidate(ActionType.GIVE_UP, 0.0, 0.0, None, Channel.NONE, attempt_number, "stop")
        )

        cands.sort(key=lambda x: x.ev_paise, reverse=True)

        top = cands[0]
        rationale.append(
            f"Timing model → best retry {best.label} (P={best.prob:.2f}); "
            f"soonest retry P={p_now:.2f}."
        )
        rationale.append(
            f"Nudge belief for {cls.value}: P={p_nudge_raw:.2f} "
            f"(quality {q:.2f}, {c.language.value}/{c.preferred_channel.value})."
        )
        if self.bandit is not None and self.bandit_observations(cls, top.action_type) > 0:
            n_obs = int(self.bandit_observations(cls, top.action_type))
            rationale.append(
                f"Bandit-adjusted P({top.action_type.value}|{cls.value})="
                f"{top.prob:.2f} from {n_obs} outcomes."
            )
        return cands, rationale

    def decide(self, case: RecoveryCase, now: datetime, attempt_number: int) -> Decision:
        cands, rationale = self._candidates(case, now, attempt_number)
        best = cands[0]
        threshold = self.config.give_up_ev_ratio * case.failure.amount_paise
        if best.action_type != ActionType.GIVE_UP and best.ev_paise < threshold:
            best = next(c for c in cands if c.action_type == ActionType.GIVE_UP)
            rationale.append(
                f"Best expected value {format_inr(int(cands[0].ev_paise))} < "
                f"{format_inr(int(threshold))} floor → give up (unrecoverable)."
            )
        else:
            rationale.append(
                f"Chose {best.action_type.value}: expected recovery "
                f"{format_inr(int(best.ev_paise))} = {best.prob:.2f} × "
                f"{format_inr(case.failure.amount_paise)}."
            )
        return Decision(
            action_type=best.action_type,
            prob=best.prob,
            ev_paise=best.ev_paise,
            when=best.when,
            channel=best.channel,
            attempt_number=attempt_number,
            candidates=cands,
            rationale=rationale,
        )

    def plan(self, case: RecoveryCase) -> Decision:
        """Diagnose + decide the first action, without executing (for API/dashboard)."""
        if case.recoverability_class is RecoverabilityClass.UNKNOWN:
            self.diagnose(case)
        decision = self.decide(
            case, case.failure.occurred_at, case.failure.attempt_number + 1
        )
        best = decision.candidates[0]
        if best.action_type in (ActionType.RETRY_OPTIMAL, ActionType.RETRY_NOW) and best.when:
            case.predicted_best_slot = _slot_label(best.when)
        for line in decision.rationale:
            case.log(line)
        return decision

    # -- stage 4: act (full episode) ---------------------------------------- #
    def run_episode(self, case: RecoveryCase, executor: Executor) -> RecoveryOutcome:
        self.diagnose(case)
        now = case.failure.occurred_at
        attempt_number = case.failure.attempt_number + 1
        case.status = CaseStatus.IN_PROGRESS
        attempts = 0
        final_action: ActionType | None = None

        for _ in range(self.config.max_steps):
            decision = self.decide(case, now, attempt_number)
            final_action = decision.action_type
            for line in decision.rationale:
                case.log(line)

            if decision.action_type == ActionType.GIVE_UP:
                case.status = CaseStatus.GAVE_UP
                break

            attempts += 1
            action = RecoveryAction(
                type=decision.action_type,
                channel=decision.channel,
                scheduled_at=decision.when,
                language=case.customer.language,
                predicted_success=decision.prob,
            )

            if decision.action_type in (ActionType.RETRY_NOW, ActionType.RETRY_OPTIMAL):
                when = decision.when or now
                result = executor.retry(case, when, attempt_number)
                attempt_number += 1
                now = when + timedelta(hours=1)
            else:  # a nudge of some flavour
                msg = self.dunning.generate(case, decision.channel, case.customer.language)
                action.message = msg.text
                action.meta["authored_by"] = msg.authored_by
                action.meta["quality"] = msg.quality
                result = executor.nudge(case, action, msg)
                now = (decision.when or now) + timedelta(days=1)

            action.executed_at = decision.when or now
            action.succeeded = result.succeeded
            if result.payment_link:
                action.payment_link = result.payment_link
            case.actions.append(action)

            if self.bandit is not None:
                self.bandit.update(
                    case.recoverability_class, decision.action_type, result.succeeded
                )

            case.log(
                f"→ {decision.action_type.value} "
                f"{'succeeded' if result.succeeded else 'failed'}"
                f"{' — ' + result.detail if result.detail else ''}."
            )

            if result.succeeded:
                case.status = CaseStatus.RECOVERED
                case.recovered_at = action.executed_at
                case.recovered_amount_paise = case.failure.amount_paise
                break
        else:
            case.status = CaseStatus.HALTED

        days = None
        if case.recovered_at is not None:
            elapsed = (case.recovered_at - case.failure.occurred_at).total_seconds()
            days = round(elapsed / 86400.0, 2)
        return RecoveryOutcome(
            case_id=case.id,
            recovered=case.status == CaseStatus.RECOVERED,
            attempts=attempts,
            revenue_recovered_paise=case.recovered_amount_paise,
            days_to_recover=days,
            final_action=final_action,
        )

    # -- helpers ------------------------------------------------------------- #
    def _soonest_slot(self, now: datetime) -> datetime:
        earliest = now + timedelta(hours=2)
        for d in range(0, 3):
            day = (now + timedelta(days=d)).replace(minute=0, second=0, microsecond=0)
            for h in sorted(CANDIDATE_HOURS):
                cand = day.replace(hour=h)
                if cand >= earliest:
                    return cand
        return earliest.replace(minute=0, second=0, microsecond=0)

    def _next_morning(self, now: datetime) -> datetime:
        base = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        return base


_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _slot_label(when: datetime) -> str:
    return f"{_DAY_NAMES[when.weekday()]} {when:%d %b %H:%M}"
