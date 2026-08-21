from recovery.domain.models import ActionType
from recovery.eval.harness import build_case


def _first(pop, reason_code):
    f = next(f for f in pop.failures if f.reason_code == reason_code)
    return build_case(f, pop.customers, pop.subscriptions)


def _engine(bundle):
    from recovery.policy.bandit import ContextualBandit
    from recovery.policy.engine import RecoveryEngine

    rm, tm = bundle
    return RecoveryEngine(rm, tm, bandit=ContextualBandit(seed=7))


def test_engine_avoids_retrying_expired_cards(trained_bundle, holdout):
    engine = _engine(trained_bundle)
    case = _first(holdout, "card_expired")
    decision = engine.plan(case)
    # retrying an expired card is futile — the engine should prefer a customer nudge
    assert decision.action_type in (
        ActionType.REQUEST_CARD_UPDATE,
        ActionType.DUNNING_NUDGE,
        ActionType.SWITCH_METHOD,
    )


def test_engine_retries_transient_failures(trained_bundle, holdout):
    engine = _engine(trained_bundle)
    case = _first(holdout, "issuer_unavailable")
    decision = engine.plan(case)
    assert decision.action_type in (ActionType.RETRY_NOW, ActionType.RETRY_OPTIMAL)


def test_engine_gives_up_on_hard_declines(trained_bundle, holdout):
    engine = _engine(trained_bundle)
    case = _first(holdout, "stolen_or_lost_card")
    decision = engine.plan(case)
    assert decision.action_type == ActionType.GIVE_UP


def test_episode_produces_a_trace(trained_bundle, holdout):
    from recovery.eval.executor import SimulatedExecutor

    engine = _engine(trained_bundle)
    env = holdout.environment()
    executor = SimulatedExecutor(env)
    case = _first(holdout, "insufficient_funds")
    outcome = engine.run_episode(case, executor)
    assert case.trace  # every decision is explained
    assert outcome.case_id == case.id
    assert case.status.value in ("recovered", "halted", "gave_up")
