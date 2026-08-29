from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


AUDIT_EVENTS = (
    "ANOMALY_DETECTED",
    "REVENUE_RISK_CALCULATED",
    "PAYMENT_INVESTIGATION",
    "CUSTOMER_ANALYSIS",
    "ROOT_CAUSE_IDENTIFIED",
    "MONEYGUARD_DECISION",
    "POLICY_DECISION",
    "RECOVERY_EXECUTED",
    "RECOVERY_VERIFIED",
)


class AuditEvent(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    trace_id: str
    incident_id: Optional[str] = None
    agent: str
    event: str
    decision: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    action: Optional[str] = None
    result: Optional[str] = None
