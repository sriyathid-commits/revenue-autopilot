"""Detect revenue at risk from failed payments and checkout events."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

AT_RISK = {"PAYMENT_FAILED", "PAYMENT_RETRY", "CHECKOUT_ABANDONED"}


def detect_revenue_risk(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    if not transactions:
        return {
            "revenue_at_risk": 0.0,
            "affected_transactions": [],
            "confidence": 0.0,
            "reason": "No transactions available.",
            "evidence": {"count": 0},
            "clusters": [],
            "decision": "none",
        }

    df = pd.DataFrame(transactions)
    df["is_at_risk"] = df["status"].isin(AT_RISK)
    flagged = df[df["is_at_risk"]].copy()

    gateway_rates = df.groupby("gateway")["is_at_risk"].mean().astype(float).to_dict()
    overall_fail = float(df["is_at_risk"].mean()) if len(df) else 0.0

    clusters: list[dict[str, Any]] = []
    if not flagged.empty:
        grouped = flagged.groupby(["gateway", "failure_reason"], dropna=False)
        for (gateway, reason), group in grouped:
            if len(group) < 1:
                continue
            rate = gateway_rates.get(gateway, 0.0)
            elevated = rate >= 0.12
            clusters.append(
                {
                    "kind": "gateway_failure",
                    "gateway": gateway,
                    "failure_reason": reason,
                    "count": int(len(group)),
                    "revenue_at_risk": round(float(group["amount"].sum()), 2),
                    "transaction_ids": group["transaction_id"].tolist(),
                    "elevated_failure_rate": elevated,
                    "gateway_failure_rate": round(rate, 4),
                    "max_risk": float(group["risk_score"].max()),
                    "max_retry": int(group["retry_count"].max()),
                    "suspicious": bool((group["retry_count"] >= 4).any() and group["risk_score"].max() >= 0.75),
                }
            )
        abandon = flagged[flagged["status"] == "CHECKOUT_ABANDONED"]
        if not abandon.empty:
            high = abandon[abandon["amount"] >= 8000]
            if not high.empty:
                clusters.append(
                    {
                        "kind": "abandonment",
                        "gateway": high["gateway"].mode().iloc[0] if not high["gateway"].mode().empty else "unknown",
                        "failure_reason": None,
                        "count": int(len(high)),
                        "revenue_at_risk": round(float(high["amount"].sum()), 2),
                        "transaction_ids": high["transaction_id"].tolist(),
                        "elevated_failure_rate": False,
                        "gateway_failure_rate": 0.0,
                        "max_risk": float(high["risk_score"].max()),
                        "max_retry": int(high["retry_count"].max()),
                        "suspicious": False,
                    }
                )

    device_groups = flagged.groupby(["customer_id", "device_id"]) if not flagged.empty else []
    for (cust, device), group in device_groups:
        span = (group["timestamp"].max() - group["timestamp"].min()).total_seconds() if len(group) > 1 else 9999
        if len(group) >= 5 and span <= 900:
            clusters.append(
                {
                    "kind": "suspicious_retry",
                    "gateway": group["gateway"].mode().iloc[0] if not group["gateway"].mode().empty else "unknown",
                    "failure_reason": group["failure_reason"].mode().iloc[0] if group["failure_reason"].notna().any() else "authentication_failed",
                    "count": int(len(group)),
                    "revenue_at_risk": round(float(group["amount"].sum()), 2),
                    "transaction_ids": group["transaction_id"].tolist(),
                    "elevated_failure_rate": True,
                    "gateway_failure_rate": 1.0,
                    "max_risk": float(group["risk_score"].max()),
                    "max_retry": int(group["retry_count"].max()),
                    "suspicious": True,
                    "customer_id": cust,
                    "device_id": device,
                    "window_seconds": span,
                }
            )

    iso_flags = 0
    if len(df) >= 20:
        try:
            from sklearn.ensemble import IsolationForest

            feats = df[["amount", "retry_count", "risk_score"]].fillna(0)
            iso = IsolationForest(n_estimators=40, contamination=0.08, random_state=42)
            iso_flags = int((iso.fit_predict(feats) == -1).sum())
        except Exception:
            iso_flags = 0

    revenue = round(float(flagged["amount"].sum()) if not flagged.empty else 0.0, 2)
    affected = flagged["transaction_id"].tolist() if not flagged.empty else []
    confidence = float(np.clip(0.45 + overall_fail * 1.6 + (0.15 if any(c.get("elevated_failure_rate") for c in clusters) else 0), 0, 0.97))
    reason = (
        f"{len(affected)} at-risk events totaling ₹{revenue:,.2f}. "
        f"Portfolio failure/abandon rate {overall_fail:.1%}."
    )
    return {
        "revenue_at_risk": revenue,
        "affected_transactions": affected,
        "confidence": round(confidence, 4),
        "reason": reason,
        "evidence": {
            "overall_at_risk_rate": round(overall_fail, 4),
            "gateway_failure_rates": {k: round(v, 4) for k, v in gateway_rates.items()},
            "cluster_count": len(clusters),
            "isolation_forest_flags": iso_flags,
        },
        "clusters": sorted(clusters, key=lambda c: c["revenue_at_risk"], reverse=True),
        "decision": "anomaly" if revenue > 0 else "none",
        "explanation": reason,
    }
