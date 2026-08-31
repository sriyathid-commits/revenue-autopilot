"""In-process async event bus — fan-out to all connected WebSocket clients."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

# Each connected WebSocket gets its own asyncio.Queue entry here.
_subscribers: list[asyncio.Queue[str]] = []


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _serialize(event_type: str, data: dict[str, Any]) -> str:
    payload = {"type": event_type, "ts": _now_iso(), **data}
    return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Subscribe / unsubscribe
# ---------------------------------------------------------------------------

def subscribe() -> asyncio.Queue[str]:
    """Register a new subscriber queue and return it."""
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue[str]) -> None:
    """Remove a subscriber queue (called when WebSocket disconnects)."""
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Publish helpers — all non-blocking (drop if queue full)
# ---------------------------------------------------------------------------

def _publish(event_type: str, data: dict[str, Any]) -> None:
    if not _subscribers:
        return
    message = _serialize(event_type, data)
    for q in list(_subscribers):
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            # Slow consumer — drop the oldest message and push the new one.
            try:
                q.get_nowait()
                q.put_nowait(message)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass


def emit_incident(incident_id: str, trace_id: str, merchant_id: str,
                  root_cause: str, action: str, status: str,
                  revenue_at_risk: float, revenue_recovered: float,
                  risk_level: str, confidence: float,
                  scenario: str | None = None) -> None:
    _publish("incident", {
        "incident_id": incident_id,
        "trace_id": trace_id,
        "merchant_id": merchant_id,
        "root_cause": root_cause,
        "action": action,
        "status": status,
        "revenue_at_risk": revenue_at_risk,
        "revenue_recovered": revenue_recovered,
        "risk_level": risk_level,
        "confidence": confidence,
        "scenario": scenario,
    })


def emit_agent_step(incident_id: str, trace_id: str, agent: str,
                    event: str, decision: str, confidence: float,
                    ok: bool) -> None:
    _publish("agent_step", {
        "incident_id": incident_id,
        "trace_id": trace_id,
        "agent": agent,
        "event": event,
        "decision": decision,
        "confidence": confidence,
        "ok": ok,
    })


def emit_metrics(metrics: dict[str, Any]) -> None:
    _publish("metrics", {"metrics": metrics})


def emit_transaction(transaction_id: str, status: str, amount: float,
                     gateway: str, merchant_id: str,
                     risk_score: float) -> None:
    _publish("transaction", {
        "transaction_id": transaction_id,
        "status": status,
        "amount": amount,
        "gateway": gateway,
        "merchant_id": merchant_id,
        "risk_score": risk_score,
    })


def emit_system(message: str, level: str = "info") -> None:
    _publish("system", {"message": message, "level": level})


def subscriber_count() -> int:
    return len(_subscribers)
