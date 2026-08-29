from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from backend.models.transaction import Transaction
from backend.services.database import IncidentRow, TransactionRow


def row_to_transaction(row: TransactionRow) -> Transaction:
    return Transaction(
        transaction_id=row.transaction_id,
        merchant_id=row.merchant_id,
        customer_id=row.customer_id,
        amount=row.amount,
        currency=row.currency,
        payment_method=row.payment_method,
        gateway=row.gateway,
        timestamp=row.timestamp,
        status=row.status,  # type: ignore[arg-type]
        failure_reason=row.failure_reason,
        device_id=row.device_id,
        customer_segment=row.customer_segment,
        cart_value=row.cart_value,
        retry_count=row.retry_count,
        risk_score=row.risk_score,
        revenue_at_risk=row.revenue_at_risk,
        recovery_status=row.recovery_status,  # type: ignore[arg-type]
        recovery_action=row.recovery_action,  # type: ignore[arg-type]
        scenario=row.scenario,
        ground_truth_anomaly=row.ground_truth_anomaly,
        ground_truth_root_cause=row.ground_truth_root_cause,
        ground_truth_suspicious=row.ground_truth_suspicious,
        ground_truth_should_recover=row.ground_truth_should_recover,
        detected_anomaly=row.detected_anomaly,
        detected_root_cause=row.detected_root_cause,
    )


def insert_transactions(session: Session, records: list[dict[str, Any]]) -> int:
    count = 0
    for rec in records:
        session.add(
            TransactionRow(
                transaction_id=rec["transaction_id"],
                merchant_id=rec["merchant_id"],
                customer_id=rec["customer_id"],
                amount=float(rec["amount"]),
                currency=rec.get("currency") or "INR",
                payment_method=rec["payment_method"],
                gateway=rec["gateway"],
                timestamp=rec["timestamp"],
                status=rec["status"],
                failure_reason=rec.get("failure_reason"),
                device_id=rec["device_id"],
                customer_segment=rec["customer_segment"],
                cart_value=float(rec["cart_value"]),
                retry_count=int(rec.get("retry_count") or 0),
                risk_score=float(rec.get("risk_score") or 0),
                revenue_at_risk=float(rec.get("revenue_at_risk") or 0),
                recovery_status=rec.get("recovery_status") or "NONE",
                recovery_action=rec.get("recovery_action") or "NONE",
                scenario=rec.get("scenario"),
                ground_truth_anomaly=bool(rec.get("ground_truth_anomaly")),
                ground_truth_root_cause=rec.get("ground_truth_root_cause"),
                ground_truth_suspicious=bool(rec.get("ground_truth_suspicious")),
                ground_truth_should_recover=bool(rec.get("ground_truth_should_recover")),
                detected_anomaly=bool(rec.get("detected_anomaly")),
                detected_root_cause=rec.get("detected_root_cause"),
            )
        )
        count += 1
    session.flush()
    return count


def list_transactions(session: Session, limit: int = 100, offset: int = 0, status: str | None = None) -> tuple[int, list[Transaction]]:
    q = session.query(TransactionRow)
    if status:
        q = q.filter(TransactionRow.status == status)
    total = q.count()
    rows = q.order_by(TransactionRow.timestamp.desc()).offset(offset).limit(limit).all()
    return total, [row_to_transaction(r) for r in rows]


def transactions_as_dicts(session: Session, ids: list[str] | None = None) -> list[dict[str, Any]]:
    q = session.query(TransactionRow)
    if ids is not None:
        q = q.filter(TransactionRow.transaction_id.in_(ids))
    return [row_to_transaction(r).model_dump() for r in q.all()]


def mark_detected(session: Session, ids: list[str], root_cause: str | None) -> None:
    if not ids:
        return
    rows = session.query(TransactionRow).filter(TransactionRow.transaction_id.in_(ids)).all()
    for row in rows:
        row.detected_anomaly = True
        if root_cause:
            row.detected_root_cause = root_cause


def mark_recovery(session: Session, ids: list[str], action: str, status: str) -> None:
    rows = session.query(TransactionRow).filter(TransactionRow.transaction_id.in_(ids)).all()
    for row in rows:
        row.recovery_action = action
        row.recovery_status = status


def parse_ids(raw: str) -> list[str]:
    try:
        data = json.loads(raw or "[]")
        return [str(x) for x in data]
    except Exception:
        return []


def incident_has_recovery(session: Session, transaction_ids: list[str]) -> bool:
    if not transaction_ids:
        return False
    q = (
        session.query(IncidentRow)
        .filter(IncidentRow.status.in_(["EXECUTED", "VERIFIED"]))
        .all()
    )
    for inc in q:
        existing = set(parse_ids(inc.transaction_ids_json))
        if existing.intersection(transaction_ids) and inc.revenue_recovered > 0:
            return True
    return False
