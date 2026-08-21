"""FastAPI backend for the AI Revenue Recovery dashboard.

Run: ``uvicorn recovery.api.app:app --reload --port 8000``
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from recovery.api.schemas import PlanRequest
from recovery.api.service import get_service
from recovery.domain.taxonomy import FAILURE_REASONS


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_service()  # warm models + sample episodes at startup
    yield


app = FastAPI(
    title="AI Revenue Recovery",
    description="Agentic recovery of failed recurring payments on Razorpay.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"service": "ai-revenue-recovery", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict:
    return get_service().health()


@app.get("/api/metrics")
def metrics() -> dict:
    return get_service().metrics()


@app.get("/api/cases")
def cases(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    reason: str | None = None,
    klass: str | None = None,
) -> dict:
    return get_service().cases(
        limit=limit, offset=offset, status=status, reason=reason, klass=klass
    )


@app.get("/api/reasons")
def reasons() -> dict:
    return {
        "reasons": [
            {
                "code": r.code,
                "description": r.description,
                "class": r.recoverability.value,
                "retry_helps": r.retry_helps,
                "prior_recover_prob": r.prior_recover_prob,
            }
            for r in FAILURE_REASONS.values()
        ]
    }


@app.post("/api/plan")
def plan(req: PlanRequest) -> dict:
    return get_service().plan(req)


@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request) -> dict:
    raw = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    return get_service().handle_webhook(raw, signature)
