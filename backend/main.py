"""Revenue Autopilot API — synthetic/test-mode financial operations only."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import demo, incidents, metrics, recovery, transactions
from backend.api.audit import router as audit_router
from backend.api.ws import router as ws_router
from backend.config import get_settings
from backend.services.database import get_engine
from backend.services.event_bus import emit_system, subscriber_count
from backend.services.stream_worker import run_stream_worker, stop_stream_worker

settings = get_settings()

_worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _worker_task
    get_engine()
    emit_system("Revenue Autopilot starting — real-time stream initialising.", level="info")
    _worker_task = asyncio.create_task(run_stream_worker(), name="stream_worker")
    try:
        yield
    finally:
        stop_stream_worker()
        if _worker_task and not _worker_task.done():
            _worker_task.cancel()
            try:
                await _worker_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Revenue Autopilot",
    description=(
        "Detect. Decide. Recover. Verify. "
        "Synthetic/test-mode data only — does not move real money. "
        "Real-time events available at /ws."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(recovery.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(ws_router)          # mounts at /ws (no prefix)


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "synthetic_test",
        "moves_real_money": False,
        "llm_required": False,
        "realtime_subscribers": subscriber_count(),
    }


@app.get("/api/stream/status")
def stream_status():
    """Quick probe for the real-time stream state."""
    return {
        "worker_running": _worker_task is not None and not _worker_task.done(),
        "subscribers": subscriber_count(),
    }
