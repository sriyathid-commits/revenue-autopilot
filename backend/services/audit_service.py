from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.models.audit import AuditEvent
from backend.services.database import AuditRow


def log_audit(
    session: Session,
    *,
    trace_id: str,
    incident_id: str | None,
    agent: str,
    event: str,
    decision: str = "",
    evidence: dict[str, Any] | None = None,
    action: str | None = None,
    result: str | None = None,
    timestamp: datetime | None = None,
) -> AuditEvent:
    ts = timestamp or datetime.utcnow()
    row = AuditRow(
        timestamp=ts,
        trace_id=trace_id,
        incident_id=incident_id,
        agent=agent,
        event=event,
        decision=decision,
        evidence_json=json.dumps(evidence or {}, default=str),
        action=action,
        result=result,
    )
    session.add(row)
    session.flush()
    return AuditEvent(
        id=row.id,
        timestamp=row.timestamp,
        trace_id=row.trace_id,
        incident_id=row.incident_id,
        agent=row.agent,
        event=row.event,
        decision=row.decision,
        evidence=json.loads(row.evidence_json or "{}"),
        action=row.action,
        result=row.result,
    )


def list_audit(session: Session, incident_id: str) -> list[AuditEvent]:
    rows = (
        session.query(AuditRow)
        .filter(AuditRow.incident_id == incident_id)
        .order_by(AuditRow.timestamp.asc(), AuditRow.id.asc())
        .all()
    )
    return [
        AuditEvent(
            id=r.id,
            timestamp=r.timestamp,
            trace_id=r.trace_id,
            incident_id=r.incident_id,
            agent=r.agent,
            event=r.event,
            decision=r.decision,
            evidence=json.loads(r.evidence_json or "{}"),
            action=r.action,
            result=r.result,
        )
        for r in rows
    ]
