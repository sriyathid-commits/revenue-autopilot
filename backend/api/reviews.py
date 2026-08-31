"""Human Review queue — incidents routed to manual approval/rejection."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.services.audit_service import log_audit
from backend.services.database import AgentResultRow, IncidentRow, get_db
from backend.services.transaction_service import parse_ids
from backend.utils import sanitize_nan

router = APIRouter()

REVIEW_STATUSES = {"HUMAN_REVIEW", "PENDING"}
REVIEW_ACTIONS  = {"HUMAN_REVIEW", "STOP"}


def _needs_review(row: IncidentRow) -> bool:
    return row.action in REVIEW_ACTIONS and row.status not in {
        "APPROVED", "REJECTED", "VERIFIED", "BLOCKED"
    }


def _format(row: IncidentRow, agents: list) -> dict:
    # Pull useful agent fields for the review card.
    mg = next((a for a in agents if a.agent == "moneyguard"), None)
    rc = next((a for a in agents if a.agent == "root_cause"), None)
    pol = next((a for a in agents if a.agent == "policy_engine"), None)

    mg_payload: dict = sanitize_nan(json.loads(mg.payload_json or "{}")) if mg else {}
    pol_payload: dict = sanitize_nan(json.loads(pol.payload_json or "{}")) if pol else {}
    rc_payload: dict = sanitize_nan(json.loads(rc.payload_json or "{}")) if rc else {}

    return {
        "incident_id": row.incident_id,
        "trace_id": row.trace_id,
        "merchant_id": row.merchant_id,
        "amount": row.amount,
        "currency": row.currency,
        "root_cause": row.root_cause,
        "risk_level": row.risk_level,
        "action": row.action,
        "status": row.status,
        "confidence": row.confidence,
        "revenue_at_risk": row.revenue_at_risk,
        "transaction_ids": parse_ids(row.transaction_ids_json),
        "created_at": row.created_at.isoformat(),
        "scenario": row.scenario,
        # Agent-derived fields for the review card
        "moneyguard_decision": mg.decision if mg else row.action,
        "moneyguard_reason": mg_payload.get("reason") or row.moneyguard_reason,
        "policy_reason": pol_payload.get("reason") or row.policy_reason,
        "root_cause_explanation": rc_payload.get("explanation") or "",
        "review_reason": pol_payload.get("reason") or mg_payload.get("reason") or "Manual review required.",
        "retry_count": int(pol_payload.get("checks", {}).get("retry_count") or 0),
        "ai_recommendation": mg.decision if mg else row.action,
        "review_completed": row.status in {"APPROVED", "REJECTED"},
    }


@router.get("/reviews")
def list_reviews(db: Session = Depends(get_db)):
    rows = (
        db.query(IncidentRow)
        .filter(IncidentRow.action.in_(REVIEW_ACTIONS))
        .order_by(IncidentRow.created_at.desc())
        .all()
    )
    result = []
    for row in rows:
        agents = db.query(AgentResultRow).filter(
            AgentResultRow.incident_id == row.incident_id
        ).all()
        result.append(_format(row, agents))
    return {"total": len(result), "items": result}


class ReviewAction(BaseModel):
    action: str  # "APPROVE" or "REJECT"
    reason: str = ""


@router.post("/reviews/{incident_id}")
def submit_review(
    incident_id: str,
    body: ReviewAction,
    db: Session = Depends(get_db),
):
    if body.action not in {"APPROVE", "REJECT"}:
        raise HTTPException(400, "action must be APPROVE or REJECT")

    row = db.query(IncidentRow).filter(
        IncidentRow.incident_id == incident_id
    ).one_or_none()
    if not row:
        raise HTTPException(404, "Incident not found")

    if row.status in {"APPROVED", "REJECTED"}:
        raise HTTPException(409, f"Review already completed: {row.status}")

    now = datetime.utcnow()
    if body.action == "APPROVE":
        row.status = "APPROVED"
        row.action = "HUMAN_APPROVED"
        row.updated_at = now
        result_msg = "Human reviewer approved — test-mode action logged."
    else:
        row.status = "REJECTED"
        row.updated_at = now
        result_msg = "Human reviewer rejected — no financial action taken."

    reason = body.reason or f"Human {body.action.lower()} via review queue."

    log_audit(
        db,
        trace_id=row.trace_id,
        incident_id=incident_id,
        agent="human_reviewer",
        event="HUMAN_REVIEW_DECISION",
        decision=body.action,
        evidence={"reason": reason, "action": body.action},
        action=body.action,
        result=result_msg,
        timestamp=now,
    )

    db.flush()

    agents = db.query(AgentResultRow).filter(
        AgentResultRow.incident_id == incident_id
    ).all()

    return {
        "ok": True,
        "incident_id": incident_id,
        "new_status": row.status,
        "message": result_msg,
        "review": _format(row, agents),
    }
