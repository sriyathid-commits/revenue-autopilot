"""Estimate customer intent, conversion, and recovery probability."""

from __future__ import annotations

from typing import Any

import pandas as pd


def analyze_customers(
    transactions: list[dict[str, Any]],
    cluster: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not transactions:
        return {
            "intent": "unknown",
            "conversion_probability": 0.0,
            "recovery_probability": 0.0,
            "confidence": 0.2,
            "evidence": {},
            "decision": "unknown",
            "explanation": "No customer data.",
        }

    df = pd.DataFrame(transactions)
    ids = set(cluster.get("transaction_ids") or []) if cluster else set()
    focus = df[df["transaction_id"].isin(ids)] if ids else df
    if focus.empty:
        focus = df

    segment = str(focus["customer_segment"].mode().iloc[0]) if not focus.empty else "mass"
    cart = float(focus["cart_value"].median()) if not focus.empty else 0.0
    retries = int(focus["retry_count"].mean()) if not focus.empty else 0
    abandoned = bool((focus["status"] == "CHECKOUT_ABANDONED").any()) if not focus.empty else False
    suspicious = bool(cluster.get("suspicious")) if cluster else bool((focus["retry_count"] >= 5).any())

    intent = "complete_purchase"
    conversion = 0.42
    recovery = 0.38
    if suspicious:
        intent = "possible_abuse_or_credential_testing"
        conversion = 0.08
        recovery = 0.02
    elif abandoned and segment in {"premium", "enterprise", "affluent"}:
        intent = "high_intent_abandonment"
        conversion = 0.61
        recovery = 0.48
    elif retries >= 2 and not suspicious:
        intent = "retrying_to_complete"
        conversion = 0.55
        recovery = 0.52
    elif segment == "mass" and cart < 1000:
        intent = "price_sensitive"
        conversion = 0.28
        recovery = 0.22

    explanation = (
        f"Segment {segment}, median cart ₹{cart:,.0f}, retries {retries}. "
        f"Intent: {intent}."
    )
    return {
        "intent": intent,
        "conversion_probability": conversion,
        "recovery_probability": recovery,
        "customer_segment": segment,
        "confidence": 0.74 if not suspicious else 0.86,
        "evidence": {
            "segment": segment,
            "median_cart_value": round(cart, 2),
            "mean_retry_count": retries,
            "abandonment": abandoned,
            "suspicious": suspicious,
        },
        "decision": intent,
        "explanation": explanation,
    }
