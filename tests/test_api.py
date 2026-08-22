"""Service-level API tests (no disk models required — models are injected)."""

import hashlib
import hmac
import json

from recovery.api.schemas import PlanRequest
from recovery.api.service import RecoveryService
from recovery.config import get_settings


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
        PlanRequest(
            reason_code="card_expired",
            amount_paise=99900,
            language="hi",
            create_payment_link=True,
        )
    )
    assert rec["decision"]["action"] in (
        "request_card_update",
        "dunning_nudge",
        "switch_method",
    )
    assert rec["message"]["text"]  # a localised message was generated
    assert rec["payment_link"]["short_url"].startswith("http")
    assert rec["trace"]


def _failed_event() -> bytes:
    return json.dumps(
        {
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
    ).encode()


def test_webhook_unsigned_rejected(trained_bundle, holdout):
    # No secret configured → fail CLOSED (503), never process an unsigned event.
    svc = _service(trained_bundle, holdout)
    out = svc.handle_webhook(_failed_event(), signature=None)
    assert out["ok"] is False
    assert out["status"] == 503


def test_webhook_bad_signature_rejected(trained_bundle, holdout, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsec_test")
    get_settings.cache_clear()
    svc = _service(trained_bundle, holdout)
    out = svc.handle_webhook(_failed_event(), signature="deadbeef")
    assert out["ok"] is False
    assert out["status"] == 401


def test_webhook_valid_signature_and_idempotency(trained_bundle, holdout, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsec_test")
    get_settings.cache_clear()
    svc = _service(trained_bundle, holdout)
    body = _failed_event()
    sig = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()

    out = svc.handle_webhook(body, signature=sig, event_id="evt_1")
    assert out["ok"] and out["handled"]
    assert out["case"]["decision"]["action"]

    # Replaying the same event id is a no-op (at-least-once delivery guard).
    dup = svc.handle_webhook(body, signature=sig, event_id="evt_1")
    assert dup["handled"] is False
    assert dup["reason"] == "duplicate event"


def test_scheduler_fires_jobs_and_closes_loop(trained_bundle, holdout):
    svc = _service(trained_bundle, holdout)
    # Planning a (non-give-up) case persists it and enqueues a scheduled job.
    svc.plan(PlanRequest(reason_code="insufficient_funds", amount_paise=49900))
    assert svc.store.pending_job_count() >= 1
    out = svc.fire_due_jobs(fire_all=True)  # demo fast-forward
    assert out["fired"] >= 1
    assert svc.store.pending_job_count() == 0  # all fired → loop closed


def test_confirm_recovery_marks_case(trained_bundle, holdout):
    svc = _service(trained_bundle, holdout)
    rec = svc.plan(PlanRequest(reason_code="insufficient_funds", amount_paise=49900))
    assert svc.confirm_recovery(rec["id"]) is True
    got = svc.store.get_case(rec["id"])
    assert got["recovered"] is True and got["recovery_source"] == "webhook"
    assert svc.store.recovered_count() >= 1


def test_check_recoveries_polls_and_confirms(trained_bundle, holdout):
    svc = _service(trained_bundle, holdout)
    # a case with a REAL (non-mock) payment link, not yet recovered
    svc.store.save_case(
        {
            "id": "case_poll",
            "class": "insufficient_funds",
            "recovered": False,
            "amount_paise": 49900,
            "decision": {"action": "retry_optimal", "prob": 0.5},
            "payment_link": {"id": "plink_X", "is_mock": False, "short_url": "http://x"},
        }
    )
    out = svc.check_recoveries()  # mock gateway reports the link 'paid'
    assert out["checked"] >= 1 and out["confirmed"] >= 1
    assert svc.store.get_case("case_poll")["recovered"] is True


def test_webhook_recovery_confirmation_closes_the_loop(trained_bundle, holdout, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsec_test")
    get_settings.cache_clear()
    svc = _service(trained_bundle, holdout)
    rec = svc.plan(PlanRequest(reason_code="insufficient_funds", amount_paise=49900))
    event = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_OK", "notes": {"case_id": rec["id"]}}}},
    }
    body = json.dumps(event).encode()
    sig = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()
    out = svc.handle_webhook(body, signature=sig, event_id="evt_cap_1")
    assert out["handled"] is True and out["event"] == "recovery_confirmation"
    assert svc.store.get_case(rec["id"])["recovered"] is True
