from backend.agents.orchestrator import run_incident_pipeline
from backend.agents.revenue_agent import detect_revenue_risk
from backend.config import get_settings
from backend.services.database import get_session_factory, reset_engine
from backend.services.transaction_service import insert_transactions
from simulator.generator import dataframe_to_records, generate_transactions


def test_suspicious_retry_pipeline_no_auto_recovery(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path.as_posix()}/pipe.db")
    get_settings.cache_clear()
    reset_engine()
    session = get_session_factory()()
    recs = dataframe_to_records(generate_transactions(n=80, scenario="demo_unsafe", seed=11))
    insert_transactions(session, recs)
    det = detect_revenue_risk(recs)
    cluster = None
    for c in det["clusters"]:
        if c.get("suspicious"):
            cluster = c
            break
    assert cluster is not None
    result = run_incident_pipeline(session, recs, cluster, det, scenario="demo_unsafe")
    session.commit()
    assert result["action"] in {"STOP", "HUMAN_REVIEW"}
    assert result["revenue_recovered"] == 0
    session.close()
    get_settings.cache_clear()
    reset_engine()


def test_risk_calculation_on_failed_status():
    recs = dataframe_to_records(generate_transactions(n=100, scenario="gateway_degradation", seed=1))
    failed = [r for r in recs if r["status"] in {"PAYMENT_FAILED", "PAYMENT_RETRY", "CHECKOUT_ABANDONED"}]
    assert all(r["revenue_at_risk"] == r["amount"] for r in failed)
