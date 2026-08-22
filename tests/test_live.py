"""Live recovery campaign — the streaming engine-vs-baseline race."""

from recovery.live import SCENARIOS, run_campaign


def test_scenarios_available():
    assert {"balanced", "expired_cards", "insufficient_funds"} <= set(SCENARIOS)


def test_campaign_streams_and_engine_wins_on_expired_cards(trained_bundle):
    rm, tm = trained_bundle
    events = list(run_campaign(rm, tm, n=50, scenario="expired_cards", seed=99))

    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "done"
    cases = [e for e in events if e["type"] == "case"]
    assert len(cases) == 50

    # On an expired-card-heavy book the engine (requests card updates) should clearly
    # beat the fixed-retry baseline (uselessly re-hits dead cards).
    s = events[-1]["summary"]
    assert s["engine_rate"] > s["baseline_rate"]

    # event shape the frontend relies on
    c = cases[10]
    assert "reason" in c["case"] and "amount_paise" in c["case"]
    assert "recovered" in c["engine"] and "recovered" in c["baseline"]
    assert "rate" in c["totals"]["engine"] and "revenue_paise" in c["totals"]["engine"]
