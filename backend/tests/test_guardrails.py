from backend.agents.moneyguard_agent import evaluate_moneyguard
from backend.policies.policy_engine import policy_engine
from backend.models.transaction import RecoveryAction


def test_moneyguard_blocks_suspicious_retry():
    result = evaluate_moneyguard(
        root_cause="risk_signal",
        confidence=0.95,
        risk_score=0.9,
        amount=999,
        retry_count=9,
        suspicious_retry=True,
        duplicate_action=False,
    )
    assert result["approved"] is False
    assert result["action"] == "STOP"


def test_moneyguard_allows_low_risk_gateway():
    result = evaluate_moneyguard(
        root_cause="gateway_degradation",
        confidence=0.9,
        risk_score=0.2,
        amount=2500,
        retry_count=1,
        suspicious_retry=False,
        duplicate_action=False,
    )
    assert result["approved"] is True
    assert result["action"] == "ALTERNATE_PAYMENT"


def test_policy_high_value_human_review():
    decision = policy_engine.evaluate(
        proposed_action=RecoveryAction.SAFE_RETRY,
        risk_score=0.2,
        confidence=0.9,
        amount=80_000,
        retry_count=0,
        customer_risk=0.1,
        duplicate_action=False,
        suspicious_retry=False,
        root_cause="temporary_failure",
    )
    assert decision.allowed is False
    assert decision.requires_human_review is True
    assert decision.action == RecoveryAction.HUMAN_REVIEW


def test_policy_duplicate_stop():
    decision = policy_engine.evaluate(
        proposed_action=RecoveryAction.ALTERNATE_PAYMENT,
        risk_score=0.1,
        confidence=0.9,
        amount=500,
        retry_count=0,
        customer_risk=0.1,
        duplicate_action=True,
        suspicious_retry=False,
    )
    assert decision.action == RecoveryAction.STOP
    assert decision.allowed is False


def test_policy_low_confidence():
    decision = policy_engine.evaluate(
        proposed_action=RecoveryAction.SAFE_RETRY,
        risk_score=0.1,
        confidence=0.2,
        amount=500,
        retry_count=0,
        customer_risk=0.1,
        duplicate_action=False,
        suspicious_retry=False,
    )
    assert decision.requires_human_review
