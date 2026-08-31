"""Background async worker — continuously generates and processes synthetic transactions.

Runs as a long-lived asyncio task inside the FastAPI lifespan. Each cycle:
  1. Generates a small batch of synthetic transactions.
  2. Inserts them into the database.
  3. Runs the agent pipeline on detected clusters.
  4. Emits real-time events to all WebSocket subscribers.
  5. Sleeps for CYCLE_SECONDS before the next batch.

This is test/demo mode only — no real money is moved.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from backend.services.event_bus import (
    emit_incident,
    emit_metrics,
    emit_system,
    emit_transaction,
    subscriber_count,
)

logger = logging.getLogger(__name__)

# Tunable constants
CYCLE_SECONDS = 8          # seconds between each streaming batch
BATCH_SIZE = 20            # synthetic transactions per batch
MAX_INCIDENTS_PER_CYCLE = 2  # cap pipeline runs per cycle to keep it snappy
SCENARIOS = ["mixed", "gateway_degradation", "checkout_abandonment",
             "repeated_failures", "suspicious_retry"]

_running = False


async def run_stream_worker() -> None:
    """Entry-point called from lifespan. Runs until cancelled."""
    global _running
    _running = True
    emit_system("Real-time stream worker started.", level="info")
    logger.info("Stream worker started.")

    cycle = 0
    while _running:
        try:
            await _one_cycle(cycle)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Stream worker cycle error: %s", exc)
            emit_system(f"Stream cycle error: {exc}", level="warn")
        cycle += 1
        await asyncio.sleep(CYCLE_SECONDS)

    emit_system("Real-time stream worker stopped.", level="info")
    logger.info("Stream worker stopped.")


def stop_stream_worker() -> None:
    global _running
    _running = False


async def _one_cycle(cycle: int) -> None:
    """Run one streaming cycle in a thread pool to avoid blocking the event loop."""
    # Only emit transactions when someone is watching (saves CPU in idle state).
    # Still run the pipeline occasionally to keep the DB alive.
    has_subscribers = subscriber_count() > 0

    # Run blocking DB / CPU work in a thread so the event loop stays free.
    result = await asyncio.get_event_loop().run_in_executor(
        None, _sync_cycle, cycle, has_subscribers
    )

    if result is None:
        return

    transactions, incidents, metrics = result

    # Emit individual transaction events.
    if has_subscribers:
        for tx in transactions[:BATCH_SIZE]:
            emit_transaction(
                transaction_id=str(tx.get("transaction_id", "")),
                status=str(tx.get("status", "")),
                amount=float(tx.get("amount", 0)),
                gateway=str(tx.get("gateway", "")),
                merchant_id=str(tx.get("merchant_id", "")),
                risk_score=float(tx.get("risk_score", 0)),
            )

    # Emit incident events.
    for inc in incidents:
        emit_incident(
            incident_id=str(inc.get("incident_id", "")),
            trace_id=str(inc.get("trace_id", "")),
            merchant_id=str(inc.get("merchant_id", "")),
            root_cause=str(inc.get("root_cause", "unknown")),
            action=str(inc.get("action", "NONE")),
            status=str(inc.get("status", "PENDING")),
            revenue_at_risk=float(inc.get("revenue_at_risk", 0)),
            revenue_recovered=float(inc.get("revenue_recovered", 0)),
            risk_level=str(inc.get("risk_level", "MEDIUM")),
            confidence=float(inc.get("confidence", 0)),
            scenario=inc.get("scenario"),
        )

    # Emit updated metrics snapshot.
    if metrics and has_subscribers:
        emit_metrics(metrics)


def _sync_cycle(cycle: int, emit_txs: bool):
    """Synchronous DB work — runs in a thread executor."""
    import random
    from simulator.generator import dataframe_to_records, generate_transactions
    from backend.agents.orchestrator import run_batch
    from backend.services.database import get_session_factory
    from backend.services.transaction_service import insert_transactions
    from backend.services.metrics_service import compute_metrics

    scenario = SCENARIOS[cycle % len(SCENARIOS)]
    seed = (cycle * 17 + 3) % 100_000  # deterministic but varied per cycle

    try:
        df = generate_transactions(n=BATCH_SIZE, scenario=scenario, seed=seed)
    except ValueError:
        # n < 20 guard — shouldn't happen but be safe
        return None

    records = dataframe_to_records(df)

    db = get_session_factory()()
    try:
        insert_transactions(db, records)
        incidents = run_batch(db, records, max_incidents=MAX_INCIDENTS_PER_CYCLE)
        metrics = compute_metrics(db)
        db.commit()
        return records, incidents, metrics
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
