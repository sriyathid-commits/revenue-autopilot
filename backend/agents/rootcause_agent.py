"""Combine investigator and customer evidence into a single root cause."""

from __future__ import annotations

from typing import Any

from backend.models.transaction import RootCause


def identify_root_cause(
    payment: dict[str, Any],
    customer: dict[str, Any],
    revenue: dict[str, Any],
    cluster: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = list(payment.get("root_cause_candidates") or ["unknown"])
    suspicious = bool(cluster and cluster.get("suspicious")) or customer.get("intent") == "possible_abuse_or_credential_testing"
    kind = (cluster or {}).get("kind")

    if suspicious or kind == "suspicious_retry":
        cause = RootCause.RISK_SIGNAL.value
        confidence = 0.93
        explanation = "Rapid repeated attempts from the same customer/device dominate the evidence."
    elif kind == "abandonment" or "customer_abandonment" in candidates:
        cause = RootCause.CUSTOMER_ABANDONMENT.value
        confidence = 0.82
        explanation = "High-value checkout abandonment with remaining purchase intent."
    elif "gateway_degradation" in candidates:
        cause = RootCause.GATEWAY_DEGRADATION.value
        confidence = 0.89
        explanation = "Clustered gateway failures far above the 4–5% baseline."
    elif "retry_problem" in candidates:
        cause = RootCause.RETRY_PROBLEM.value
        confidence = 0.78
        explanation = "Repeated legitimate retries after payment failure."
    elif "temporary_failure" in candidates:
        cause = RootCause.TEMPORARY_FAILURE.value
        confidence = 0.7
        explanation = "Transient network/gateway timeouts without a systemic cluster."
    elif "payment_method_failure" in candidates:
        cause = RootCause.PAYMENT_METHOD_FAILURE.value
        confidence = 0.72
        explanation = "Issuer/method declines concentrated on one payment method."
    else:
        cause = RootCause.UNKNOWN.value
        confidence = 0.4
        explanation = "Insufficient structure to name a specific root cause."

    evidence = {
        "payment_candidates": candidates,
        "customer_intent": customer.get("intent"),
        "cluster_kind": kind,
        "revenue_at_risk": revenue.get("revenue_at_risk"),
    }
    return {
        "root_cause": cause,
        "confidence": confidence,
        "evidence": evidence,
        "explanation": explanation,
        "decision": cause,
    }
