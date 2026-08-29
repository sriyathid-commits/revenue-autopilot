from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.agents.orchestrator import rerun_recovery, run_batch
from backend.evaluation import evaluate
from backend.services.database import get_db
from backend.services.transaction_service import insert_transactions
from simulator.generator import dataframe_to_records, generate_transactions

router = APIRouter()


class SimulatorRequest(BaseModel):
    n: int = Field(1000, description="Transaction count")
    scenario: str = "mixed"
    seed: int = 42
    run_pipeline: bool = True


@router.post("/simulator/run")
def run_simulator(body: SimulatorRequest, db: Session = Depends(get_db)):
    n = body.n
    if n > 50_000:
        raise HTTPException(400, "Maximum 50,000 synthetic transactions")
    try:
        df = generate_transactions(n=n, scenario=body.scenario, seed=body.seed)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    records = dataframe_to_records(df)
    inserted = insert_transactions(db, records)
    incidents = []
    if body.run_pipeline:
        max_inc = 20 if n <= 1000 else 30
        incidents = run_batch(db, records, max_incidents=max_inc)
    evaluation = evaluate(db)
    return {
        "inserted": inserted,
        "scenario": body.scenario,
        "incidents": incidents,
        "evaluation": evaluation,
    }


@router.post("/recovery/{incident_id}")
def recover_incident(incident_id: str, db: Session = Depends(get_db)):
    try:
        result = rerun_recovery(db, incident_id)
    except KeyError:
        raise HTTPException(404, "Incident not found") from None
    return result
