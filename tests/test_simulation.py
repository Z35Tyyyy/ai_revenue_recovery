from datetime import datetime, timezone

from recovery.domain.models import Channel, Language, RecoverabilityClass
from recovery.simulation.generator import generate_population
from recovery.simulation.history import build_training_logs


def _at(day, hour):
    return datetime(2026, 9, day, hour, tzinfo=timezone.utc)


def test_population_is_reproducible():
    a = generate_population(n_customers=200, n_failures=500, seed=7)
    b = generate_population(n_customers=200, n_failures=500, seed=7)
    assert [f.id for f in a.failures] == [f.id for f in b.failures]
    assert [f.reason_code for f in a.failures] == [f.reason_code for f in b.failures]


def test_environment_dynamics_are_sane():
    pop = generate_population(n_customers=400, n_failures=1200, seed=7)
    env = pop.environment()

    # insufficient funds: retrying near payday must beat retrying far from it
    inf = next(f for f in pop.failures if f.reason_code == "insufficient_funds")
    cust = pop.customers[inf.customer_id]
    lat = env.latent(inf.id)
    near_day = min(cust.salary_day + 1, 28)
    far_day = ((cust.salary_day + 18 - 1) % 28) + 1
    assert lat.retry_prob(_at(near_day, 10), 1) > lat.retry_prob(_at(far_day, 10), 1)

    # expired card: bare retry is near-useless
    ce = next(f for f in pop.failures if f.reason_code == "card_expired")
    assert env.latent(ce.id).retry_prob(_at(10, 10), 1) < 0.15

    # hard decline: essentially dead
    hd = next(f for f in pop.failures if f.reason_code == "stolen_or_lost_card")
    assert env.latent(hd.id).retry_prob(_at(10, 10), 1) < 0.05


def test_resolution_is_deterministic():
    pop = generate_population(n_customers=100, n_failures=300, seed=7)
    env = pop.environment()
    f = pop.failures[0]
    r1 = env.resolve_retry(f.id, _at(5, 10), 1)
    r2 = env.resolve_retry(f.id, _at(5, 10), 1)
    assert r1 == r2


def test_dunning_personalisation_helps():
    pop = generate_population(n_customers=400, n_failures=1200, seed=7)
    env = pop.environment()
    ce = next(f for f in pop.failures if f.reason_code == "card_expired")
    cust = pop.customers[ce.customer_id]
    lat = env.latent(ce.id)
    matched = lat.dunning_prob(cust.preferred_channel, cust.language, cust, 1.0)
    other_channel = Channel.SMS if cust.preferred_channel != Channel.SMS else Channel.EMAIL
    generic = lat.dunning_prob(other_channel, Language.EN, cust, 0.8)
    assert matched >= generic


def test_training_logs_have_learnable_signal():
    pop = generate_population(n_customers=400, n_failures=1200, seed=7)
    timing, cases = build_training_logs(pop, seed=7)
    assert {"label", "near_salary", "salary_sensitive"}.issubset(timing.columns)
    assert {"label", "recoverability", "amount_paise"}.issubset(cases.columns)

    ss = timing[timing.salary_sensitive == 1.0]
    near = ss[ss.near_salary == 1.0].label.mean()
    far = ss[ss.near_salary == 0.0].label.mean()
    assert near > far  # timing signal is present for salary-sensitive failures

    by_class = cases.groupby("recoverability").label.mean()
    assert by_class[RecoverabilityClass.TRANSIENT.value] > by_class[
        RecoverabilityClass.HARD_DECLINE.value
    ]
