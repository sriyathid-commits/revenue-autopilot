from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from backend.models.transaction import RecoveryAction, RecoveryStatus


class Incident(BaseModel):
    incident_id: str
    merchant_id: str
    amount: float
    currency: str = "INR"
    root_cause: Optional[str] = None
    risk_level: str = "MEDIUM"
    action: RecoveryAction = RecoveryAction.NONE
    status: RecoveryStatus = RecoveryStatus.PENDING
    trace_id: str
    scenario: Optional[str] = None
    revenue_at_risk: float = 0.0
    revenue_recovered: float = 0.0
    confidence: float = 0.0
    transaction_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class IncidentDetail(Incident):
    explanation: str = ""
    moneyguard_reason: str = ""
    policy_reason: str = ""
    verified: bool = False
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
