from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.models.transaction import TransactionListResponse
from backend.services.database import IncidentRow, get_db
from backend.services.transaction_service import list_transactions, parse_ids, row_to_transaction

router = APIRouter()


@router.get("/transactions")
def get_transactions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    total, items = list_transactions(db, limit=limit, offset=offset, status=status)
    return TransactionListResponse(total=total, items=items)
