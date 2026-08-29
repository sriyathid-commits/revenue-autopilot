from backend.agents.verification_agent import verify_recovery
from backend.services.metrics_service import compute_metrics
from backend.services.recovery_service import simulate_recovery
from backend.services.database import get_session_factory, reset_engine
from backend.config import get_settings


def test_recovery_alternate_payment_gateway():
    result = simulate_recovery(
        action="ALTERNATE_PAYMENT",
        root_cause="gateway_degradation",
        amount=12000,
        allowed=True,
        transaction_count=8,
    )
    assert result["action"] == "ALTERNATE_PAYMENT"
    assert "revenue_recovered" in result
    if result["success"]:
        assert result["revenue_recovered"] == 12000
        assert result["payment_outcome"] == "PAYMENT_SUCCESS"
    else:
        assert result["revenue_recovered"] == 0


def test_recovery_blocked_when_not_allowed():
    result = simulate_recovery(
        action="ALTERNATE_PAYMENT",
        root_cause="gateway_degradation",
        amount=12000,
        allowed=False,
    )
    assert result["success"] is False
    assert result["revenue_recovered"] == 0


def test_verification_never_counts_unconfirmed():
    sim = {"success": False, "revenue_recovered": 0, "action": "SAFE_RETRY", "policy_compliant": True}
    v = verify_recovery(simulator_result=sim, policy_allowed=True, moneyguard_approved=True, duplicate=False)
    assert v["revenue_recovered"] == 0
    assert v["final_status"] == "FAILED"


def test_verification_stop_zero_revenue():
    sim = {"success": False, "revenue_recovered": 0, "action": "STOP", "policy_compliant": True}
    v = verify_recovery(simulator_result=sim, policy_allowed=False, moneyguard_approved=False, duplicate=False)
    assert v["verified"] is True
    assert v["revenue_recovered"] == 0
    assert v["final_status"] == "STOP"


def test_empty_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path.as_posix()}/t.db")
    get_settings.cache_clear()
    reset_engine()
    session = get_session_factory()()
    m = compute_metrics(session)
    session.close()
    assert m["gmv"] == 0
    assert m["transactions"] == 0
    assert m["revenue_recovered"] == 0
    get_settings.cache_clear()
    reset_engine()
