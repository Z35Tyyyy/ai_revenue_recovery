"""Service-level API tests (no disk models required — models are injected)."""

import json

from recovery.api.schemas import PlanRequest
from recovery.api.service import RecoveryService


def _service(trained_bundle, holdout):
    rm, tm = trained_bundle
    return RecoveryService(
        sample_size=40, recovery_model=rm, timing_model=tm, population=holdout
    )


def test_health_and_metrics(trained_bundle, holdout):
    svc = _service(trained_bundle, holdout)
    h = svc.health()
    assert h["status"] == "ok" and h["models_loaded"] is True
    m = svc.metrics()
    assert m["live_sample"]["total"] == 40
    assert 0.0 <= m["live_sample"]["recovery_rate"] <= 1.0


def test_cases_stream_and_filter(trained_bundle, holdout):
    svc = _service(trained_bundle, holdout)
    all_cases = svc.cases(limit=100)
    assert all_cases["total"] == 40
    assert all(c["trace"] for c in all_cases["cases"])
    # filtering by class returns a subset
    some_class = all_cases["cases"][0]["class"]
    filtered = svc.cases(limit=100, klass=some_class)
    assert filtered["total"] <= all_cases["total"]
    assert all(c["class"] == some_class for c in filtered["cases"])


def test_interactive_plan_expired_card(trained_bundle, holdout):
    svc = _service(trained_bundle, holdout)
    rec = svc.plan(
        PlanRequest(reason_code="card_expired", amount_paise=99900, language="hi")
    )
    assert rec["decision"]["action"] in (
        "request_card_update",
        "dunning_nudge",
        "switch_method",
    )
    assert rec["message"]["text"]  # a localised message was generated
    assert rec["payment_link"]["short_url"].startswith("http")
    assert rec["trace"]


def test_webhook_ingestion(trained_bundle, holdout):
    svc = _service(trained_bundle, holdout)
    event = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_WH1",
                    "amount": 49900,
                    "method": "upi",
                    "error_reason": "insufficient_funds",
                    "notes": {},
                }
            }
        },
    }
    out = svc.handle_webhook(json.dumps(event).encode(), signature=None)
    assert out["ok"] and out["handled"]
    assert out["case"]["decision"]["action"]
