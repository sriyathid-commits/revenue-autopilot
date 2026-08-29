"""Evaluation against synthetic ground truth. Metrics are computed, never hard-coded."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from backend.services.database import EvaluationRow, IncidentRow, TransactionRow
from backend.services.transaction_service import parse_ids


def evaluate(session: Session) -> dict:
    txs = session.query(TransactionRow).all()
    incidents = session.query(IncidentRow).all()
    if not txs:
        payload = _zeros()
        payload["note"] = "Database empty — run the simulator or live demo first."
        return payload

    y_true = [1 if t.ground_truth_anomaly else 0 for t in txs]
    y_pred = [1 if t.detected_anomaly else 0 for t in txs]
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    labeled = [t for t in txs if t.detected_root_cause and t.ground_truth_root_cause]
    rc_ok = sum(1 for t in labeled if t.detected_root_cause == t.ground_truth_root_cause)
    rc_acc = rc_ok / len(labeled) if labeled else 0.0

    recovered = sum(i.revenue_recovered for i in incidents)
    at_risk_detected = sum(t.amount for t in txs if t.detected_anomaly)
    gt_at_risk = sum(t.amount for t in txs if t.ground_truth_anomaly)

    auto_attempts = [i for i in incidents if i.action not in {"STOP", "HUMAN_REVIEW", "NONE"}]
    successes = [i for i in auto_attempts if i.revenue_recovered > 0]
    recovery_success_rate = len(successes) / len(auto_attempts) if auto_attempts else 0.0

    false_int = 0
    for inc in incidents:
        if inc.revenue_recovered <= 0:
            continue
        ids = parse_ids(inc.transaction_ids_json)
        members = [t for t in txs if t.transaction_id in set(ids)]
        if members and all(not t.ground_truth_should_recover for t in members):
            false_int += 1
    false_rate = false_int / len(incidents) if incidents else 0.0
    human_rate = (sum(1 for i in incidents if i.action == "HUMAN_REVIEW") / len(incidents)) if incidents else 0.0

    payload = {
        "detection_precision": round(precision, 4),
        "detection_recall": round(recall, 4),
        "root_cause_accuracy": round(rc_acc, 4),
        "recovery_success_rate": round(recovery_success_rate, 4),
        "false_intervention_rate": round(false_rate, 4),
        "human_escalation_rate": round(human_rate, 4),
        "revenue_at_risk_detected": round(float(at_risk_detected), 2),
        "ground_truth_revenue_at_risk": round(float(gt_at_risk), 2),
        "revenue_recovered": round(float(recovered), 2),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "transactions_evaluated": len(txs),
        "incidents_evaluated": len(incidents),
        "labeled_root_cause_transactions": len(labeled),
    }
    session.add(EvaluationRow(created_at=datetime.utcnow(), payload_json=json.dumps(payload)))
    session.flush()
    return payload


def latest_evaluation(session: Session) -> dict:
    row = session.query(EvaluationRow).order_by(EvaluationRow.id.desc()).first()
    if row:
        return json.loads(row.payload_json)
    return evaluate(session)


def _zeros() -> dict:
    return {
        "detection_precision": 0.0,
        "detection_recall": 0.0,
        "root_cause_accuracy": 0.0,
        "recovery_success_rate": 0.0,
        "false_intervention_rate": 0.0,
        "human_escalation_rate": 0.0,
        "revenue_at_risk_detected": 0.0,
        "ground_truth_revenue_at_risk": 0.0,
        "revenue_recovered": 0.0,
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "transactions_evaluated": 0,
        "incidents_evaluated": 0,
        "labeled_root_cause_transactions": 0,
    }
