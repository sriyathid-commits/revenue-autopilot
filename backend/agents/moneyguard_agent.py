"""MoneyGuard: AI proposes, MoneyGuard evaluates — never executes money movement."""

from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.models.transaction import RecoveryAction


def evaluate_moneyguard(
    *,
    root_cause: str,
    confidence: float,
    risk_score: float,
    amount: float,
    retry_count: int,
    suspicious_retry: bool,
    duplicate_action: bool,
    proposed_action: RecoveryAction | None = None,
    customer_recovery_probability: float = 0.4,
) -> dict[str, Any]:
    settings = get_settings()
    proposal = proposed_action or _propose(root_cause, customer_recovery_probability)
    reasons: list[str] = []

    if duplicate_action:
        return _result(RecoveryAction.STOP, "HIGH", False, "Duplicate action blocked.", proposal, risk_score, confidence, amount)
    if suspicious_retry or root_cause == "risk_signal":
        return _result(
            RecoveryAction.STOP,
            "HIGH",
            True,
            "SUSPICIOUS RETRY: MoneyGuard forbids automatic recovery.",
            proposal,
            risk_score,
            confidence,
            amount,
        )
    if risk_score >= settings.high_risk_threshold:
        return _result(
            RecoveryAction.HUMAN_REVIEW,
            "HIGH",
            True,
            "HIGH RISK: escalate; AI cannot execute financial actions.",
            proposal,
            risk_score,
            confidence,
            amount,
        )
    if confidence < settings.low_confidence_threshold:
        return _result(
            RecoveryAction.HUMAN_REVIEW,
            "MEDIUM",
            True,
            "LOW CONFIDENCE: human review required.",
            proposal,
            risk_score,
            confidence,
            amount,
        )
    if amount >= settings.high_value_threshold:
        return _result(
            RecoveryAction.HUMAN_REVIEW,
            "HIGH",
            True,
            "VERY HIGH VALUE: human authorization required.",
            proposal,
            risk_score,
            confidence,
            amount,
        )
    if retry_count >= 8:
        return _result(
            RecoveryAction.HUMAN_REVIEW,
            "HIGH",
            True,
            "Retry volume exceeds safe automatic bounds.",
            proposal,
            risk_score,
            confidence,
            amount,
        )

    reasons.append("HIGH CONFIDENCE + LOW RISK: bounded test-mode recovery may proceed after policy check.")
    return {
        "approved": True,
        "action": proposal.value,
        "risk_level": "LOW",
        "requires_human_review": False,
        "reason": " ".join(reasons),
        "proposed_action": proposal.value,
        "confidence": confidence,
        "evidence": {
            "risk_score": risk_score,
            "amount": amount,
            "retry_count": retry_count,
            "root_cause": root_cause,
        },
        "decision": proposal.value,
        "explanation": " ".join(reasons),
    }


def _propose(root_cause: str, recovery_p: float) -> RecoveryAction:
    if root_cause == "gateway_degradation":
        return RecoveryAction.ALTERNATE_PAYMENT
    if root_cause == "payment_method_failure":
        return RecoveryAction.ALTERNATE_PAYMENT
    if root_cause == "customer_abandonment":
        return RecoveryAction.PERSONALIZED_OFFER if recovery_p >= 0.3 else RecoveryAction.RECOVERY_MESSAGE
    if root_cause in {"retry_problem", "temporary_failure"}:
        return RecoveryAction.SAFE_RETRY
    return RecoveryAction.HUMAN_REVIEW


def _result(
    action: RecoveryAction,
    risk_level: str,
    human: bool,
    reason: str,
    proposal: RecoveryAction,
    risk_score: float,
    confidence: float,
    amount: float,
) -> dict[str, Any]:
    return {
        "approved": False,
        "action": action.value,
        "risk_level": risk_level,
        "requires_human_review": human,
        "reason": reason,
        "proposed_action": proposal.value,
        "confidence": confidence,
        "evidence": {"risk_score": risk_score, "amount": amount},
        "decision": action.value,
        "explanation": reason,
    }
