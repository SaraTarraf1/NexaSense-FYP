from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.equipment import Equipment
from app.models.user import User
from app.schemas.history import (
    HistoryFault, HistoryHealth, HistoryInspection, HistoryPage, HistoryReading, HistorySummary,
)
from app.services.history_service import History

router = APIRouter(prefix="/api/equipment/{equipment_id}/history", tags=["History"])


def history_query(
    equipment_id: int,
    response: Response,
    start: Annotated[AwareDatetime, Query(description="Inclusive observation time.")],
    end: Annotated[AwareDatetime, Query(description="Exclusive observation time.")],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> History:
    equipment = db.scalar(select(Equipment.id).where(Equipment.id == equipment_id, Equipment.user_id == user.id))
    if equipment is None:
        raise HTTPException(404, "Equipment not found.")
    start, end = (datetime.astimezone(value, timezone.utc) for value in (start, end))
    if start >= end:
        raise HTTPException(422, "The end must be later than the start.")
    response.headers["Cache-Control"] = "no-store"
    return History(db, equipment_id, user.id, bounds=(start, end))


@router.get("", response_model=HistorySummary)
def historical_summary(history: History = Depends(history_query)):
    return history.summary()


@router.get("/{section}", response_model=(
    HistoryPage[HistoryReading] | HistoryPage[HistoryFault] |
    HistoryPage[HistoryHealth] | HistoryPage[HistoryInspection]
))
def historical_records(
    section: Literal["readings", "anomalies", "faults", "health", "inspections"],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    history: History = Depends(history_query),
):
    return history.page(section, offset, limit)
