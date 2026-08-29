from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.audit_service import list_audit
from backend.services.database import IncidentRow, get_db

router = APIRouter()


@router.get("/audit/{incident_id}")
def get_audit(incident_id: str, db: Session = Depends(get_db)):
    exists = db.query(IncidentRow).filter(IncidentRow.incident_id == incident_id).first()
    if not exists:
        raise HTTPException(404, "Incident not found")
    return list_audit(db, incident_id)
