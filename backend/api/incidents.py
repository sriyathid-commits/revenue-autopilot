from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.incident import Incident, IncidentDetail
from backend.services.database import AgentResultRow, IncidentRow, get_db
from backend.services.transaction_service import parse_ids

router = APIRouter()


def _incident(row: IncidentRow) -> Incident:
    return Incident(
        incident_id=row.incident_id,
        merchant_id=row.merchant_id,
        amount=row.amount,
        currency=row.currency,
        root_cause=row.root_cause,
        risk_level=row.risk_level,
        action=row.action,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        trace_id=row.trace_id,
        scenario=row.scenario,
        revenue_at_risk=row.revenue_at_risk,
        revenue_recovered=row.revenue_recovered,
        confidence=row.confidence,
        transaction_ids=parse_ids(row.transaction_ids_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    rows = db.query(IncidentRow).order_by(IncidentRow.created_at.desc()).all()
    return {"total": len(rows), "items": [_incident(r) for r in rows]}


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    row = db.query(IncidentRow).filter(IncidentRow.incident_id == incident_id).one_or_none()
    if not row:
        raise HTTPException(404, "Incident not found")
    agents = (
        db.query(AgentResultRow)
        .filter(AgentResultRow.incident_id == incident_id)
        .order_by(AgentResultRow.id.asc())
        .all()
    )
    return IncidentDetail(
        **_incident(row).model_dump(),
        explanation=row.explanation,
        moneyguard_reason=row.moneyguard_reason,
        policy_reason=row.policy_reason,
        verified=row.verified,
        agent_results=[
            {
                "agent": a.agent,
                "confidence": a.confidence,
                "decision": a.decision,
                "explanation": a.explanation,
                "evidence": json.loads(a.evidence_json or "{}"),
                "payload": json.loads(a.payload_json or "{}"),
                "ok": a.ok,
                "error": a.error,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in agents
        ],
    )


@router.get("/agents/{incident_id}")
def get_agents(incident_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(AgentResultRow)
        .filter(AgentResultRow.incident_id == incident_id)
        .order_by(AgentResultRow.id.asc())
        .all()
    )
    if not rows:
        exists = db.query(IncidentRow).filter(IncidentRow.incident_id == incident_id).first()
        if not exists:
            raise HTTPException(404, "Incident not found")
    return [
        {
            "agent": a.agent,
            "confidence": a.confidence,
            "decision": a.decision,
            "explanation": a.explanation,
            "evidence": json.loads(a.evidence_json or "{}"),
            "payload": json.loads(a.payload_json or "{}"),
            "ok": a.ok,
            "error": a.error,
            "timestamp": a.timestamp.isoformat(),
            "trace_id": a.trace_id,
        }
        for a in rows
    ]
