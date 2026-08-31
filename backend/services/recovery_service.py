"""Test-mode recovery simulator. Never moves real money."""

from __future__ import annotations

import hashlib
from typing import Any

from backend.models.transaction import RecoveryAction


# Success probabilities tuned to produce ~35–50% overall recovery rate.
# gateway_degradation is the "recoverable" demo path — kept at 0.72 so Demo A
# clearly recovers. Other causes are lower to produce realistic mixed outcomes.
SUCCESS_BY_CAUSE = {
    "gateway_degradation": {
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.72,
        RecoveryAction.SAFE_RETRY.value: 0.22,
        RecoveryAction.RECOVERY_MESSAGE.value: 0.12,
        RecoveryAction.PERSONALIZED_OFFER.value: 0.15,
    },
    "payment_method_failure": {
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.48,
        RecoveryAction.SAFE_RETRY.value: 0.18,
    },
    "customer_abandonment": {
        RecoveryAction.PERSONALIZED_OFFER.value: 0.38,
        RecoveryAction.RECOVERY_MESSAGE.value: 0.22,
        RecoveryAction.SAFE_RETRY.value: 0.08,
    },
    "retry_problem": {
        RecoveryAction.SAFE_RETRY.value: 0.35,
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.30,
        RecoveryAction.RECOVERY_MESSAGE.value: 0.12,
    },
    "temporary_failure": {
        RecoveryAction.SAFE_RETRY.value: 0.42,
        RecoveryAction.ALTERNATE_PAYMENT.value: 0.36,
    },
    "risk_signal": {},
    "unknown": {
        RecoveryAction.RECOVERY_MESSAGE.value: 0.10,
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
