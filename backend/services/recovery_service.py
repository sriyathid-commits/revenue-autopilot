"""Test-mode recovery simulator. Never moves real money."""

from __future__ import annotations

import hashlib
from typing import Any

from backend.models.transaction import RecoveryAction


SUCCESS_BY_CAUSE = {
    "gateway_degradation": {
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.86,
        RecoveryAction.SAFE_RETRY.value: 0.28,
        RecoveryAction.RECOVERY_MESSAGE.value: 0.18,
        RecoveryAction.PERSONALIZED_OFFER.value: 0.22,
    },
    "payment_method_failure": {
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.74,
        RecoveryAction.SAFE_RETRY.value: 0.31,
    },
    "customer_abandonment": {
        RecoveryAction.PERSONALIZED_OFFER.value: 0.57,
        RecoveryAction.RECOVERY_MESSAGE.value: 0.33,
        RecoveryAction.SAFE_RETRY.value: 0.12,
    },
    "retry_problem": {
        RecoveryAction.SAFE_RETRY.value: 0.64,
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.58,
        RecoveryAction.RECOVERY_MESSAGE.value: 0.2,
    },
    "temporary_failure": {
        RecoveryAction.SAFE_RETRY.value: 0.71,
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.6,
    },
    "risk_signal": {},
    "unknown": {
        RecoveryAction.RECOVERY_MESSAGE.value: 0.15,
    },
}


def simulate_recovery(
    *,
    action: str,
    root_cause: str,
    amount: float,
    allowed: bool,
    transaction_count: int = 1,
) -> dict[str, Any]:
    if not allowed or action in {RecoveryAction.STOP.value, RecoveryAction.HUMAN_REVIEW.value, RecoveryAction.NONE.value}:
        return {
            "success": False,
            "revenue_recovered": 0.0,
            "action": action,
            "payment_outcome": "NO_ACTION",
            "policy_compliant": True,
            "explanation": "Recovery simulator did not execute a financial action.",
        }

    table = SUCCESS_BY_CAUSE.get(root_cause, {})
    p = table.get(action, 0.1)
    # Deterministic outcome from amount + action + cause (no RNG claim inflation).
    digest = hashlib.sha256(f"{amount:.2f}|{action}|{root_cause}|{transaction_count}".encode()).hexdigest()
    token = int(digest[:8], 16) / 0xFFFFFFFF
    success = token < p
    recovered = round(amount if success else 0.0, 2)
    return {
        "success": success,
        "revenue_recovered": recovered,
        "action": action,
        "payment_outcome": "PAYMENT_SUCCESS" if success else "PAYMENT_FAILED",
        "policy_compliant": True,
        "success_probability_used": p,
        "explanation": (
            f"Test-mode {action} after {root_cause}: "
            + ("payment succeeded; revenue counted." if success else "payment did not succeed; ₹0 recovered.")
        ),
    }
