from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.models.agent_result import AgentResult


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def safe_agent(name: str, trace_id: str, incident_id: str | None, fn, fallback: dict[str, Any]) -> AgentResult:
    try:
        payload = fn()
        if not isinstance(payload, dict):
            raise ValueError("Agent returned non-dict payload")
        return AgentResult(
            agent=name,
            trace_id=trace_id,
            incident_id=incident_id,
            confidence=float(payload.get("confidence", 0.0) or 0.0),
            decision=str(payload.get("decision") or payload.get("root_cause") or payload.get("action") or "ok"),
            explanation=str(payload.get("explanation") or payload.get("reason") or ""),
            evidence=dict(payload.get("evidence") or {}),
            payload=payload,
            timestamp=utcnow(),
            ok=True,
        )
    except Exception as exc:
        return AgentResult(
            agent=name,
            trace_id=trace_id,
            incident_id=incident_id,
            confidence=float(fallback.get("confidence", 0.0) or 0.0),
            decision=str(fallback.get("decision") or "fallback"),
            explanation=f"Agent fallback after error: {exc}",
            evidence=dict(fallback.get("evidence") or {}),
            payload=fallback,
            timestamp=utcnow(),
            ok=False,
            error=str(exc),
        )
