
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.equipment import Equipment
from app.models.user import User
from app.schemas.equipment_monitoring import (
    EquipmentMonitoringResponse,
)
from app.services.equipment_monitoring_service import (
    get_equipment_monitoring,
)


router = APIRouter(
    prefix="/api/equipment",
    tags=["Equipment Monitoring"],
)


@router.get(
    "/{equipment_id}/monitoring",
    response_model=EquipmentMonitoringResponse,
)
def monitor_equipment(
    equipment_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    equipment = db.scalar(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.user_id == current_user.id,
        )
    )

    if equipment is None:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found.",
        )

    response.headers["Cache-Control"] = "no-store"
    return get_equipment_monitoring(db, equipment)
