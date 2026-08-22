"""FastAPI backend for the AI Revenue Recovery dashboard.

Run: ``uvicorn recovery.api.app:app --reload --port 8000``
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from recovery.api.schemas import PlanRequest
from recovery.api.service import get_service
from recovery.config import REPO_ROOT, get_settings
from recovery.domain.taxonomy import FAILURE_REASONS

_DIST = REPO_ROOT / "frontend" / "dist"


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

# Restrict CORS to the configured origins (default: the local dev + served origins).
# Set RECOVERY_CORS_ORIGINS="*" to allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guard mutating/costly endpoints when RECOVERY_API_KEY is configured.

    Unset (the zero-config demo default) leaves the endpoint open.
    """
    key = get_settings().api_key
    if key and x_api_key != key:
        raise HTTPException(status_code=401, detail="invalid or missing API key")


@app.get("/health")
def health() -> dict:
    return get_service().health()


@app.get("/api/metrics")
def metrics() -> dict:
    return get_service().metrics()


@app.get("/api/cases")
def cases(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
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


@app.post("/api/plan", dependencies=[Depends(require_api_key)])
def plan(req: PlanRequest) -> dict:
    return get_service().plan(req)


@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request) -> dict:
    raw = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    event_id = request.headers.get("X-Razorpay-Event-Id")
    # Offload the sync, CPU-bound handler (model inference) off the event loop.
    result = await run_in_threadpool(
        get_service().handle_webhook, raw, signature, event_id
    )
    status = result.pop("status", None)
    if status:
        raise HTTPException(status_code=status, detail=result.get("error", "error"))
    return result


# --------------------------------------------------------------------------- #
# Serve the built React app from the same origin (single-process deployment).
# When frontend/dist is absent (dev), the API runs standalone and you use Vite.
# --------------------------------------------------------------------------- #
_API_PREFIXES = ("api/", "webhooks/")
_API_EXACT = {"health", "openapi.json", "docs", "redoc"}

if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Real API paths that fell through should 404 as JSON, not as index.html.
        if full_path.startswith(_API_PREFIXES) or full_path in _API_EXACT:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(_DIST / "index.html")

else:

    @app.get("/")
    def root() -> dict:
        return {
            "service": "ai-revenue-recovery",
            "docs": "/docs",
            "health": "/health",
            "note": "frontend not built — run `make build-frontend` or use the Vite dev server",
        }
