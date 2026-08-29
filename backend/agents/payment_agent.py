"""Investigate gateway, method, failure reason, baseline, and retry patterns."""

from __future__ import annotations

from typing import Any

import pandas as pd

AT_RISK = {"PAYMENT_FAILED", "PAYMENT_RETRY", "CHECKOUT_ABANDONED"}


def investigate_payments(
    transactions: list[dict[str, Any]],
    cluster: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not transactions:
        return {
            "root_cause_candidates": ["unknown"],
            "failure_cluster": {},
            "confidence": 0.2,
            "evidence": {},
            "decision": "unknown",
            "explanation": "No payment data to investigate.",
        }

    df = pd.DataFrame(transactions)
    ids = set(cluster.get("transaction_ids") or []) if cluster else set()
    focus = df[df["transaction_id"].isin(ids)] if ids else df[df["status"].isin(AT_RISK)]
    if focus.empty:
        focus = df

    baseline = df.copy()
    gw = str(cluster.get("gateway") if cluster else (focus["gateway"].mode().iloc[0] if not focus.empty else "unknown"))
    gw_rate = float(baseline[baseline["gateway"] == gw]["status"].isin(AT_RISK).mean()) if len(baseline) else 0.0
    other_rate = float(baseline[baseline["gateway"] != gw]["status"].isin(AT_RISK).mean()) if (baseline["gateway"] != gw).any() else gw_rate
    method_counts = focus["payment_method"].value_counts().to_dict() if "payment_method" in focus else {}
    reasons = focus["failure_reason"].dropna().value_counts().to_dict() if "failure_reason" in focus else {}
    retries = int(focus["retry_count"].max()) if not focus.empty else 0
    window = None
    if not focus.empty:
        window = {
            "start": str(focus["timestamp"].min()),
            "end": str(focus["timestamp"].max()),
            "count": int(len(focus)),
        }

    candidates: list[str] = []
    if cluster and cluster.get("suspicious"):
        candidates.append("risk_signal")
    if gw_rate >= 0.12 and gw_rate > other_rate * 1.4:
        candidates.append("gateway_degradation")
    if reasons and next(iter(reasons)) in {"do_not_honor", "issuer_declined"} and gw_rate < 0.12:
        candidates.append("payment_method_failure")
    if (focus["status"] == "CHECKOUT_ABANDONED").any() if not focus.empty else False:
        candidates.append("customer_abandonment")
    if retries >= 3:
        candidates.append("retry_problem")
    if "gateway_timeout" in reasons or "network_error" in reasons:
        candidates.append("temporary_failure")
    if not candidates:
        candidates.append("unknown")

    confidence = 0.55
    if "gateway_degradation" in candidates:
        confidence = 0.88
    if "risk_signal" in candidates:
        confidence = 0.91
    if "customer_abandonment" in candidates:
        confidence = 0.8

    evidence = {
        "gateway": gw,
        "gateway_failure_rate": round(gw_rate, 4),
        "peer_gateway_failure_rate": round(other_rate, 4),
        "historical_baseline": 0.045,
        "payment_methods": {str(k): int(v) for k, v in method_counts.items()},
        "failure_reasons": {str(k): int(v) for k, v in reasons.items()},
        "max_retry_count": retries,
        "time_window": window,
    }
    explanation = (
        f"Gateway {gw} failure rate {gw_rate:.1%} vs peer {other_rate:.1%} "
        f"(baseline ~4.5%). Dominant reasons: {list(reasons.keys())[:3]}."
    )
    return {
        "root_cause_candidates": candidates,
        "failure_cluster": {
            "gateway": gw,
            "count": int(len(focus)),
            "revenue": round(float(focus["amount"].sum()), 2) if not focus.empty else 0.0,
        },
        "confidence": confidence,
        "evidence": evidence,
        "decision": candidates[0],
        "explanation": explanation,
    }
