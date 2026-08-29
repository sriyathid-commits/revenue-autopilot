"""Verify simulated recovery outcomes. Never claims recovery without simulator confirmation."""

from __future__ import annotations

from typing import Any


def verify_recovery(
    *,
    simulator_result: dict[str, Any],
    policy_allowed: bool,
    moneyguard_approved: bool,
    duplicate: bool,
) -> dict[str, Any]:
    recovered = float(simulator_result.get("revenue_recovered") or 0.0)
    success = bool(simulator_result.get("success"))
    action = str(simulator_result.get("action") or "NONE")
    policy_ok = bool(simulator_result.get("policy_compliant", policy_allowed))

    verified = False
    final_status = "FAILED"
    reason = "Recovery not confirmed."

    if action in {"STOP", "HUMAN_REVIEW", "NONE"}:
        verified = True
        final_status = action
        recovered = 0.0
        reason = "No automatic financial action; verification confirms zero recovered revenue."
    elif duplicate:
        verified = True
        final_status = "BLOCKED"
        recovered = 0.0
        reason = "Duplicate recovery blocked; revenue not counted twice."
    elif not moneyguard_approved or not policy_allowed:
        verified = True
        final_status = "BLOCKED"
        recovered = 0.0
        reason = "Guardrail blocked execution; no revenue recovered."
    elif success and recovered > 0 and policy_ok:
        verified = True
        final_status = "VERIFIED"
        reason = f"Simulator confirmed payment success. ₹{recovered:,.2f} recovered in test mode."
    else:
        verified = True
        final_status = "FAILED"
        recovered = 0.0
        reason = "Simulator did not confirm a successful payment outcome."

    return {
        "verified": verified,
        "revenue_recovered": round(recovered, 2),
        "final_status": final_status,
        "evidence": {
            "simulator_success": success,
            "policy_compliant": policy_ok,
            "moneyguard_approved": moneyguard_approved,
            "duplicate": duplicate,
            "action": action,
        },
        "decision": final_status,
        "explanation": reason,
        "confidence": 0.95 if verified else 0.3,
    }
