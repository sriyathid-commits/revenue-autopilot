from backend.agents.revenue_agent import detect_revenue_risk
from simulator.generator import dataframe_to_records, generate_transactions


def test_detects_revenue_at_risk():
    recs = dataframe_to_records(generate_transactions(n=200, scenario="gateway_degradation", seed=4))
    result = detect_revenue_risk(recs)
    assert result["revenue_at_risk"] > 0
    assert result["affected_transactions"]
    assert 0 <= result["confidence"] <= 1


def test_empty_detection():
    result = detect_revenue_risk([])
    assert result["revenue_at_risk"] == 0
    assert result["affected_transactions"] == []
