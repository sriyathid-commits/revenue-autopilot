from fastapi import APIRouter, HTTPException

from backend.agents.orchestrator import run_incident_pipeline
from backend.evaluation import evaluate
from backend.services.database import get_session_factory, reset_database
from backend.services.metrics_service import compute_metrics
from backend.services.transaction_service import insert_transactions
from simulator.generator import dataframe_to_records, generate_transactions

router = APIRouter()


@router.post("/demo/reset")
def demo_reset():
    reset_database()
    return {"ok": True, "message": "Synthetic database reset."}


@router.post("/demo/run")
def demo_run():
    """Run Demo A (recoverable gateway degradation) and Demo B (unsafe retries)."""
    # Reset first so repeated runs stay idempotent and do not share a dropped schema.
    reset_database()
    db = get_session_factory()()
    try:
        df_a = generate_transactions(n=120, scenario="demo_recoverable", seed=7)
        df_b = generate_transactions(n=80, scenario="demo_unsafe", seed=11)
        rec_a = dataframe_to_records(df_a)
        rec_b = dataframe_to_records(df_b)
        insert_transactions(db, rec_a + rec_b)

        from backend.agents.revenue_agent import detect_revenue_risk

        det_a = detect_revenue_risk(rec_a)
        det_b = detect_revenue_risk(rec_b)

        cluster_a = _pick_cluster(det_a, prefer_suspicious=False)
        cluster_b = _pick_cluster(det_b, prefer_suspicious=True)

        result_a = run_incident_pipeline(db, rec_a, cluster_a, det_a, scenario="demo_recoverable")
        result_b = run_incident_pipeline(db, rec_b, cluster_b, det_b, scenario="demo_unsafe")

        evaluation = evaluate(db)
        metrics = compute_metrics(db)
        db.commit()
        return {
            "scenarios": [
                {
                    "id": "DEMO_A",
                    "name": "Recoverable Revenue",
                    "description": "Gateway degradation → MoneyGuard allows bounded alternate payment.",
                    **result_a,
                },
                {
                    "id": "DEMO_B",
                    "name": "Unsafe Action",
                    "description": "Suspicious retries → MoneyGuard STOP / human review. No automatic money movement.",
                    **result_b,
                },
            ],
            "metrics": metrics,
            "evaluation": evaluation,
            "message": "Live demo used synthetic/test-mode data only.",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Demo failed: {exc}") from exc
    finally:
        db.close()


def _pick_cluster(detection: dict, prefer_suspicious: bool) -> dict:
    clusters = detection.get("clusters") or []
    if prefer_suspicious:
        for c in clusters:
            if c.get("suspicious") or c.get("kind") == "suspicious_retry":
                return c
    else:
        for c in clusters:
            if not c.get("suspicious") and c.get("kind") != "suspicious_retry":
                return c
    if clusters:
        return clusters[0]
    return {
        "transaction_ids": detection.get("affected_transactions") or [],
        "revenue_at_risk": detection.get("revenue_at_risk") or 0,
        "max_risk": 0.3,
        "max_retry": 1,
        "suspicious": prefer_suspicious,
        "kind": "suspicious_retry" if prefer_suspicious else "gateway_failure",
        "gateway": "razorpay_test",
    }
