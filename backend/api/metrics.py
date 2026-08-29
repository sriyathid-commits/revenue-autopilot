from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.evaluation import latest_evaluation
from backend.services.database import get_db
from backend.services.metrics_service import compute_metrics

router = APIRouter()


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    return compute_metrics(db)


@router.get("/evaluation")
def get_evaluation(db: Session = Depends(get_db)):
    return latest_evaluation(db)
