"""Deterministic, explainable authorization for recovery actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.config import get_settings
from backend.models.transaction import RecoveryAction


@dataclass
class PolicyDecision:
    allowed: bool
    action: RecoveryAction
    risk_level: str
    requires_human_review: bool
    reason: str
    checks: dict[str, Any]


class PolicyEngine:
    def evaluate(
        self,
        *,
        proposed_action: RecoveryAction,
        risk_score: float,
        confidence: float,
        amount: float,
        retry_count: int,
        customer_risk: float,
        duplicate_action: bool,
        suspicious_retry: bool,
        root_cause: str | None = None,
    ) -> PolicyDecision:
        settings = get_settings()
        checks = {
            "risk_score": risk_score,
            "confidence": confidence,
            "amount": amount,
            "retry_count": retry_count,
            "customer_risk": customer_risk,
            "duplicate_action": duplicate_action,
            "suspicious_retry": suspicious_retry,
            "high_value_threshold": settings.high_value_threshold,
            "high_risk_threshold": settings.high_risk_threshold,
            "low_confidence_threshold": settings.low_confidence_threshold,
            "root_cause": root_cause,
        }

        if proposed_action in {RecoveryAction.STOP, RecoveryAction.HUMAN_REVIEW, RecoveryAction.NONE}:
            human = proposed_action == RecoveryAction.HUMAN_REVIEW
            return PolicyDecision(
                allowed=False,
                action=proposed_action,
                risk_level=_risk_level(risk_score, amount, settings.high_value_threshold),
                requires_human_review=human,
                reason="Proposed action is non-executing; no automatic recovery.",
                checks=checks,
            )

        if duplicate_action:
            return PolicyDecision(
                allowed=False,
                action=RecoveryAction.STOP,
                risk_level="HIGH",
                requires_human_review=False,
                reason="Duplicate-action risk: recovery already executed for these transactions.",
                checks=checks,
            )

        if suspicious_retry:
            return PolicyDecision(
                allowed=False,
                action=RecoveryAction.STOP,
                risk_level="HIGH",
                requires_human_review=True,
                reason="Suspicious retry pattern requires STOP (no automatic financial action).",
                checks=checks,
            )

        if risk_score >= settings.high_risk_threshold or customer_risk >= settings.high_risk_threshold:
            return PolicyDecision(
                allowed=False,
                action=RecoveryAction.HUMAN_REVIEW,
                risk_level="HIGH",
                requires_human_review=True,
                reason="HIGH RISK: policy forbids automatic recovery.",
                checks=checks,
            )

        if confidence < settings.low_confidence_threshold:
            return PolicyDecision(
                allowed=False,
                action=RecoveryAction.HUMAN_REVIEW,
                risk_level=_risk_level(risk_score, amount, settings.high_value_threshold),
                requires_human_review=True,
                reason="LOW CONFIDENCE: escalate to human review.",
                checks=checks,
            )

        if amount >= settings.high_value_threshold:
            return PolicyDecision(
                allowed=False,
                action=RecoveryAction.HUMAN_REVIEW,
                risk_level="HIGH",
                requires_human_review=True,
                reason="VERY HIGH VALUE: human authorization required.",
                checks=checks,
            )

        if retry_count >= 8:
            return PolicyDecision(
                allowed=False,
                action=RecoveryAction.HUMAN_REVIEW,
                risk_level="HIGH",
                requires_human_review=True,
                reason="Excessive retry count indicates possible abuse.",
                checks=checks,
            )

        bounded = _bound_action(proposed_action, root_cause)
        return PolicyDecision(
            allowed=True,
            action=bounded,
            risk_level="LOW",
            requires_human_review=False,
            reason="HIGH CONFIDENCE + LOW RISK: bounded recovery authorized in test mode.",
            checks=checks,
        )


def _bound_action(action: RecoveryAction, root_cause: str | None) -> RecoveryAction:
    mapping = {
        "gateway_degradation": RecoveryAction.ALTERNATE_PAYMENT,
        "payment_method_failure": RecoveryAction.ALTERNATE_PAYMENT,
        "customer_abandonment": RecoveryAction.PERSONALIZED_OFFER,
        "retry_problem": RecoveryAction.SAFE_RETRY,
        "temporary_failure": RecoveryAction.SAFE_RETRY,
    }
    if root_cause in mapping:
        return mapping[root_cause]
    if action in {
        RecoveryAction.SAFE_RETRY,
        RecoveryAction.ALTERNATE_PAYMENT,
        RecoveryAction.PERSONALIZED_OFFER,
        RecoveryAction.RECOVERY_MESSAGE,
    }:
        return action
    return RecoveryAction.RECOVERY_MESSAGE


def _risk_level(risk_score: float, amount: float, high_value: float) -> str:
    if risk_score >= 0.75 or amount >= high_value:
        return "HIGH"
    if risk_score >= 0.4:
        return "MEDIUM"
    return "LOW"


policy_engine = PolicyEngine()
