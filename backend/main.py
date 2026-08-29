"""Revenue Autopilot API — synthetic/test-mode financial operations only."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import demo, incidents, metrics, recovery, transactions
from backend.api.audit import router as audit_router
from backend.config import get_settings
from backend.services.database import get_engine

settings = get_settings()

app = FastAPI(
    title="Revenue Autopilot",
    description="Detect. Decide. Recover. Verify. Synthetic/test-mode data only — does not move real money.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
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


@app.on_event("startup")
def startup() -> None:
    get_engine()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "synthetic_test",
        "moves_real_money": False,
        "llm_required": False,
    }
