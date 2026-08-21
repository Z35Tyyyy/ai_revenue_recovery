from recovery.ml.train import train_recovery_model, train_timing_model
from recovery.simulation.generator import generate_population
from recovery.simulation.history import build_training_logs


def test_models_learn_and_beat_chance():
    pop = generate_population(n_customers=400, n_failures=1500, seed=7)
    timing, cases = build_training_logs(pop, seed=7)

    _, rec_metrics = train_recovery_model(cases, seed=7)
    _, tim_metrics = train_timing_model(timing, seed=7)

    # Both models must extract real signal from the noisy observational logs.
    assert rec_metrics["roc_auc"] > 0.65
    assert tim_metrics["roc_auc"] > 0.70


def test_timing_model_prefers_better_slots_than_naive():
    from datetime import timedelta

    pop = generate_population(n_customers=400, n_failures=1500, seed=7)
    timing, _ = build_training_logs(pop, seed=7)
    model, _ = train_timing_model(timing, seed=7)

    lifts = []
    inf = [f for f in pop.failures if f.reason_code == "insufficient_funds"][:80]
    for f in inf:
        c = pop.customers[f.customer_id]
        s = pop.subscriptions[f.subscription_id]
        best = model.best_slot(f, c, s, f.occurred_at, attempt_number=2)
        naive = model.score_slot(
            f, c, s, (f.occurred_at + timedelta(days=1)).replace(hour=10, minute=0), 2
        )
        lifts.append(best.prob - naive)
    assert sum(lifts) / len(lifts) > 0.03  # model finds materially better windows
