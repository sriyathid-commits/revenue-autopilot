from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    agent: str
    trace_id: str
    incident_id: Optional[str] = None
    confidence: float = 0.0
    decision: str = ""
    explanation: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    ok: bool = True
    error: Optional[str] = None
