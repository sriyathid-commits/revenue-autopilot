from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.services.database import AuditRow, IncidentRow, TransactionRow

AT_RISK = ("PAYMENT_FAILED", "PAYMENT_RETRY", "CHECKOUT_ABANDONED")
SUCCESS_STATUSES = ("PAYMENT_SUCCESS", "SETTLEMENT_COMPLETED", "SETTLEMENT_PENDING")


def compute_metrics(session: Session) -> dict:
    tx_count = session.query(func.count(TransactionRow.transaction_id)).scalar() or 0
    if tx_count == 0:
        return _empty_metrics()

    gmv = session.query(func.coalesce(func.sum(TransactionRow.amount), 0.0)).filter(
        TransactionRow.status.in_(SUCCESS_STATUSES)
    ).scalar() or 0.0

    revenue_at_risk = session.query(func.coalesce(func.sum(TransactionRow.amount), 0.0)).filter(
        TransactionRow.status.in_(AT_RISK)
    ).scalar() or 0.0

    recovered = session.query(func.coalesce(func.sum(IncidentRow.revenue_recovered), 0.0)).scalar() or 0.0
    potential = session.query(func.coalesce(func.sum(IncidentRow.revenue_at_risk), 0.0)).scalar() or 0.0

    interventions = session.query(func.count(IncidentRow.incident_id)).filter(
        IncidentRow.verified.is_(True), IncidentRow.revenue_recovered > 0
    ).scalar() or 0
    human = session.query(func.count(IncidentRow.incident_id)).filter(
        IncidentRow.action == "HUMAN_REVIEW"
    ).scalar() or 0
    stopped = session.query(func.count(IncidentRow.incident_id)).filter(
        IncidentRow.action == "STOP"
    ).scalar() or 0

    try:
        false_interventions = (
            session.query(func.count(IncidentRow.incident_id))
            .join(
                TransactionRow,
                TransactionRow.transaction_id == func.json_extract(IncidentRow.transaction_ids_json, "$[0]"),
            )
            .filter(IncidentRow.revenue_recovered > 0, TransactionRow.ground_truth_should_recover.is_(False))
            .scalar()
        )
    except Exception:
        false_interventions = None
    if false_interventions is None:
        false_interventions = _false_interventions(session)

    recovery_rate = (float(recovered) / float(revenue_at_risk)) if revenue_at_risk else 0.0

    fail_count = session.query(func.count(TransactionRow.transaction_id)).filter(
        TransactionRow.status.in_(("PAYMENT_FAILED", "PAYMENT_RETRY"))
    ).scalar() or 0
    failure_rate = float(fail_count) / float(tx_count) if tx_count else 0.0

    avg_ms = _avg_investigation_ms(session)

    series = _time_series(session)

    return {
        "gmv": round(float(gmv), 2),
        "transactions": int(tx_count),
        "revenue_at_risk": round(float(revenue_at_risk), 2),
        "potential_recovery": round(float(potential), 2),
        "revenue_recovered": round(float(recovered), 2),
        "recovery_rate": round(float(recovery_rate), 4),
        "successful_interventions": int(interventions),
        "human_escalations": int(human),
        "stopped_actions": int(stopped),
        "false_interventions": int(false_interventions or 0),
        "average_investigation_time": round(avg_ms / 1000.0, 4),
        "payment_failure_rate": round(failure_rate, 4),
        "currency": "INR",
        "series": series,
    }


def _false_interventions(session: Session) -> int:
    import json

    count = 0
    incidents = session.query(IncidentRow).filter(IncidentRow.revenue_recovered > 0).all()
    for inc in incidents:
        try:
            ids = json.loads(inc.transaction_ids_json or "[]")
        except Exception:
            ids = []
        if not ids:
            continue
        txs = session.query(TransactionRow).filter(TransactionRow.transaction_id.in_(ids)).all()
        if txs and all(not t.ground_truth_should_recover for t in txs):
            count += 1
    return count


def _avg_investigation_ms(session: Session) -> float:
    rows = session.query(AuditRow.incident_id, func.min(AuditRow.timestamp), func.max(AuditRow.timestamp)).filter(
        AuditRow.incident_id.isnot(None)
    ).group_by(AuditRow.incident_id).all()
    if not rows:
        return 0.0
    deltas = [(b - a).total_seconds() * 1000.0 for _, a, b in rows if a and b]
    return sum(deltas) / len(deltas) if deltas else 0.0


def _time_series(session: Session) -> dict:
    day = func.date(TransactionRow.timestamp)
    at_risk = func.sum(
        case((TransactionRow.status.in_(AT_RISK), TransactionRow.amount), else_=0.0)
    )
    fails = func.avg(case((TransactionRow.status.in_(("PAYMENT_FAILED", "PAYMENT_RETRY")), 1.0), else_=0.0))
    rows = (
        session.query(day.label("d"), at_risk.label("rar"), fails.label("fr"), func.count().label("n"))
        .group_by(day)
        .order_by(day)
        .all()
    )
    recovered_by_day = (
        session.query(func.date(IncidentRow.updated_at), func.sum(IncidentRow.revenue_recovered))
        .group_by(func.date(IncidentRow.updated_at))
        .all()
    )
    rec_map = {str(d): float(v or 0) for d, v in recovered_by_day}
    rar, rec, rates, fail = [], [], [], []
    for r in rows:
        key = str(r.d)
        rar.append({"t": key, "v": round(float(r.rar or 0), 2)})
        rec.append({"t": key, "v": round(rec_map.get(key, 0.0), 2)})
        denom = float(r.rar or 0)
        rec_v = rec_map.get(key, 0.0)
        rates.append({"t": key, "v": round(rec_v / denom, 4) if denom else 0.0})
        fail.append({"t": key, "v": round(float(r.fr or 0), 4)})
    return {
        "revenue_at_risk": rar[-14:],
        "revenue_recovered": rec[-14:],
        "recovery_rate": rates[-14:],
        "payment_failure_rate": fail[-14:],
    }


def _empty_metrics() -> dict:
    return {
        "gmv": 0.0,
        "transactions": 0,
        "revenue_at_risk": 0.0,
        "potential_recovery": 0.0,
        "revenue_recovered": 0.0,
        "recovery_rate": 0.0,
        "successful_interventions": 0,
        "human_escalations": 0,
        "stopped_actions": 0,
        "false_interventions": 0,
        "average_investigation_time": 0.0,
        "payment_failure_rate": 0.0,
        "currency": "INR",
        "series": {
            "revenue_at_risk": [],
            "revenue_recovered": [],
            "recovery_rate": [],
            "payment_failure_rate": [],
        },
    }
