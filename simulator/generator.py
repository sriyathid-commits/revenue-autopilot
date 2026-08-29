"""Synthetic transaction generator. Test-mode data only — never real money."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable

import numpy as np
import pandas as pd

from simulator.scenarios import SCENARIOS, ScenarioSpec, get_scenario

GATEWAYS = ["razorpay_test", "payu_sandbox", "stripe_test", "cashfree_test"]
METHODS = ["card", "upi", "netbanking", "wallet"]
SEGMENTS = ["mass", "affluent", "premium", "enterprise"]
MERCHANTS = ["m_shopfast", "m_paylater", "m_travelco", "m_edutech"]
FAILURE_REASONS = [
    "issuer_declined",
    "insufficient_funds",
    "gateway_timeout",
    "do_not_honor",
    "authentication_failed",
    "network_error",
]


def _rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(seed)


def _tid() -> str:
    return "txn_" + uuid.uuid4().hex[:16]


def _customer(rng: np.random.Generator) -> tuple[str, str, str]:
    cid = f"cust_{rng.integers(1, 8_000):05d}"
    device = f"dev_{rng.integers(1, 12_000):05d}"
    segment = str(rng.choice(SEGMENTS, p=[0.55, 0.25, 0.15, 0.05]))
    return cid, device, segment


def _amount(rng: np.random.Generator, segment: str) -> float:
    base = {"mass": 890, "affluent": 4200, "premium": 18500, "enterprise": 64000}[segment]
    noise = float(rng.lognormal(mean=0.15, sigma=0.55))
    return round(max(49.0, base * noise), 2)


def generate_transactions(
    n: int = 1000,
    scenario: str = "mixed",
    seed: int | None = 42,
    now: datetime | None = None,
) -> pd.DataFrame:
    if n not in {100, 1_000, 10_000, 50_000} and n < 20:
        raise ValueError("n must be at least 20 (supported demo sizes: 100, 1000, 10000, 50000)")
    spec = get_scenario(scenario) if scenario != "mixed" else None
    rng = _rng(seed)
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    rows: list[dict] = []

    if scenario == "mixed":
        mix = _mixed_allocation(n)
        for name, count in mix:
            rows.extend(_generate_batch(count, SCENARIOS[name], rng, now))
    else:
        assert spec is not None
        rows.extend(_generate_batch(n, spec, rng, now))

    df = pd.DataFrame(rows)
    return df.sort_values("timestamp").reset_index(drop=True)


def _mixed_allocation(n: int) -> list[tuple[str, int]]:
    weights = {
        "normal": 0.62,
        "gateway_degradation": 0.14,
        "checkout_abandonment": 0.08,
        "repeated_failures": 0.07,
        "suspicious_retry": 0.04,
        "legitimate_anomaly": 0.05,
    }
    counts = {k: int(n * w) for k, w in weights.items()}
    leftover = n - sum(counts.values())
    counts["normal"] += leftover
    return list(counts.items())


def _generate_batch(
    n: int, spec: ScenarioSpec, rng: np.random.Generator, now: datetime
) -> list[dict]:
    rows: list[dict] = []
    if spec.suspicious:
        rows.extend(_suspicious_cluster(max(12, min(n, 40)), spec, rng, now))
        n = max(0, n - len(rows))

    for _ in range(n):
        rows.append(_one_transaction(spec, rng, now, force_suspicious=False))
    return rows


def _suspicious_cluster(
    n: int, spec: ScenarioSpec, rng: np.random.Generator, now: datetime
) -> list[dict]:
    customer_id = f"cust_alert_{rng.integers(1000, 9999)}"
    device_id = f"dev_alert_{rng.integers(1000, 9999)}"
    rows = []
    base_ts = now - timedelta(minutes=8)
    amount = float(rng.choice([499.0, 999.0, 1499.0]))
    for i in range(n):
        ts = base_ts + timedelta(seconds=int(rng.integers(4, 18) * (i + 1)))
        rows.append(
            _record(
                spec=spec,
                rng=rng,
                ts=ts,
                customer_id=customer_id,
                device_id=device_id,
                segment="mass",
                amount=amount,
                status="PAYMENT_RETRY" if i > 0 else "PAYMENT_FAILED",
                retry_count=i + 1,
                risk_score=min(0.99, 0.82 + i * 0.01),
                failure_reason="authentication_failed",
                ground_truth_anomaly=True,
                ground_truth_root_cause="risk_signal",
                ground_truth_suspicious=True,
                ground_truth_should_recover=False,
            )
        )
    return rows


def _one_transaction(
    spec: ScenarioSpec,
    rng: np.random.Generator,
    now: datetime,
    force_suspicious: bool,
) -> dict:
    customer_id, device_id, segment = _customer(rng)
    amount = _amount(rng, segment)
    if spec.name in {"demo_recoverable", "gateway_degradation"}:
        amount = min(amount, 24_999.0)
    ts = now - timedelta(minutes=int(rng.integers(1, 24 * 60)))
    gateway = spec.target_gateway if spec.injected_failure_rate and spec.injected_failure_rate >= 0.15 and rng.random() < 0.7 else str(rng.choice(GATEWAYS))
    method = spec.target_method if gateway == spec.target_gateway and rng.random() < 0.5 else str(rng.choice(METHODS))

    if spec.legitimate_spike and rng.random() < 0.25:
        amount *= float(rng.uniform(2.5, 4.0))
        segment = "enterprise" if amount > 40000 else segment
        status = "PAYMENT_SUCCESS" if rng.random() > 0.05 else "PAYMENT_FAILED"
        return _record(
            spec, rng, ts, customer_id, device_id, segment, round(amount, 2),
            status=status,
            retry_count=0,
            risk_score=float(rng.uniform(0.05, 0.22)),
            failure_reason="issuer_declined" if status == "PAYMENT_FAILED" else None,
            ground_truth_anomaly=False,
            ground_truth_root_cause=None,
            ground_truth_suspicious=False,
            ground_truth_should_recover=False,
            extra_status_roll=True,
        )

    fail_p = spec.injected_failure_rate if spec.injected_failure_rate is not None else spec.baseline_failure_rate
    if gateway != spec.target_gateway and spec.name in {"gateway_degradation", "demo_recoverable"}:
        fail_p = spec.baseline_failure_rate

    abandon_p = 0.04 + (spec.high_value_abandon_boost if amount >= 15000 else 0.0)
    roll = float(rng.random())
    retry_count = 0
    risk = float(rng.uniform(0.04, 0.28))
    gt_anomaly = False
    gt_cause = None
    gt_suspicious = False
    gt_recover = False
    failure_reason = None
    status = "PAYMENT_SUCCESS"

    if roll < abandon_p and amount >= 8000:
        status = "CHECKOUT_ABANDONED"
        gt_anomaly = True
        gt_cause = "customer_abandonment"
        gt_recover = segment in {"premium", "enterprise", "affluent"}
        risk = float(rng.uniform(0.15, 0.4))
    elif roll < abandon_p + fail_p:
        status = "PAYMENT_FAILED"
        failure_reason = "gateway_timeout" if spec.name in {"gateway_degradation", "demo_recoverable"} and gateway == spec.target_gateway else str(rng.choice(FAILURE_REASONS))
        gt_anomaly = fail_p >= 0.12 or spec.retry_storm
        if spec.name in {"gateway_degradation", "demo_recoverable"} and gateway == spec.target_gateway:
            gt_anomaly = True
            gt_cause = "gateway_degradation"
            gt_recover = True
        elif spec.retry_storm and not spec.suspicious:
            gt_cause = "retry_problem"
            retry_count = int(rng.integers(2, 6))
            status = "PAYMENT_RETRY"
            gt_recover = True
            gt_anomaly = True
        elif spec.suspicious or force_suspicious:
            gt_cause = "risk_signal"
            gt_suspicious = True
            gt_recover = False
            retry_count = int(rng.integers(4, 12))
            status = "PAYMENT_RETRY"
            risk = float(rng.uniform(0.8, 0.97))
        else:
            gt_cause = "temporary_failure" if failure_reason in {"network_error", "gateway_timeout"} else "payment_method_failure"
            gt_recover = failure_reason in {"network_error", "gateway_timeout"}
            gt_anomaly = gt_cause != "payment_method_failure" or rng.random() < 0.15
            retry_count = int(rng.integers(0, 2))
    elif roll < abandon_p + fail_p + 0.03:
        status = "PAYMENT_STARTED"
    elif roll < abandon_p + fail_p + 0.08:
        status = "SETTLEMENT_PENDING"
    elif roll < abandon_p + fail_p + 0.16:
        status = "SETTLEMENT_COMPLETED"
    else:
        status = "PAYMENT_SUCCESS"

    if spec.name == "normal":
        gt_anomaly = False
        gt_recover = False
        gt_suspicious = False
        if status in {"PAYMENT_FAILED", "PAYMENT_RETRY"}:
            gt_cause = "temporary_failure"
            gt_anomaly = False

    return _record(
        spec, rng, ts, customer_id, device_id, segment, amount,
        status=status,
        retry_count=retry_count,
        risk_score=min(0.99, risk),
        failure_reason=failure_reason,
        ground_truth_anomaly=gt_anomaly,
        ground_truth_root_cause=gt_cause,
        ground_truth_suspicious=gt_suspicious,
        ground_truth_should_recover=gt_recover,
        gateway=gateway,
        method=method,
    )


def _record(
    spec: ScenarioSpec,
    rng: np.random.Generator,
    ts: datetime,
    customer_id: str,
    device_id: str,
    segment: str,
    amount: float,
    status: str,
    retry_count: int,
    risk_score: float,
    failure_reason: str | None,
    ground_truth_anomaly: bool,
    ground_truth_root_cause: str | None,
    ground_truth_suspicious: bool,
    ground_truth_should_recover: bool,
    gateway: str | None = None,
    method: str | None = None,
    extra_status_roll: bool = False,
) -> dict:
    at_risk_statuses = {"PAYMENT_FAILED", "PAYMENT_RETRY", "CHECKOUT_ABANDONED"}
    revenue_at_risk = round(amount, 2) if status in at_risk_statuses else 0.0
    merchant = str(rng.choice(MERCHANTS))
    return {
        "transaction_id": _tid(),
        "merchant_id": merchant,
        "customer_id": customer_id,
        "amount": round(amount, 2),
        "currency": "INR",
        "payment_method": method or str(rng.choice(METHODS)),
        "gateway": gateway or spec.target_gateway,
        "timestamp": ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts)),
        "status": status,
        "failure_reason": failure_reason,
        "device_id": device_id,
        "customer_segment": segment,
        "cart_value": round(amount * float(rng.uniform(1.0, 1.15)), 2),
        "retry_count": retry_count,
        "risk_score": round(float(risk_score), 4),
        "revenue_at_risk": revenue_at_risk,
        "recovery_status": "NONE",
        "recovery_action": "NONE",
        "scenario": spec.name,
        "ground_truth_anomaly": ground_truth_anomaly,
        "ground_truth_root_cause": ground_truth_root_cause,
        "ground_truth_suspicious": ground_truth_suspicious,
        "ground_truth_should_recover": ground_truth_should_recover,
        "detected_anomaly": False,
        "detected_root_cause": None,
    }


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    records = df.to_dict(orient="records")
    for rec in records:
        ts = rec["timestamp"]
        if hasattr(ts, "to_pydatetime"):
            rec["timestamp"] = ts.to_pydatetime()
        rec["ground_truth_anomaly"] = bool(rec["ground_truth_anomaly"])
        rec["ground_truth_suspicious"] = bool(rec["ground_truth_suspicious"])
        rec["ground_truth_should_recover"] = bool(rec["ground_truth_should_recover"])
        rec["detected_anomaly"] = bool(rec.get("detected_anomaly") or False)
        if rec.get("ground_truth_root_cause") is not None and not isinstance(rec["ground_truth_root_cause"], str):
            rec["ground_truth_root_cause"] = None if pd.isna(rec["ground_truth_root_cause"]) else str(rec["ground_truth_root_cause"])
        if rec.get("failure_reason") is not None and not isinstance(rec["failure_reason"], str):
            rec["failure_reason"] = None if pd.isna(rec["failure_reason"]) else str(rec["failure_reason"])
    return records


def generate_many(sizes: Iterable[int] = (100, 1000), scenario: str = "mixed", seed: int = 42) -> dict[int, pd.DataFrame]:
    return {size: generate_transactions(n=size, scenario=scenario, seed=seed + size) for size in sizes}
