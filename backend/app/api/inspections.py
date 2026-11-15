
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate,
    InspectionResponse,
)
from app.services.inspection_service import (
    InspectionError,
    start_inspection,
    finish_inspection,
)


router = APIRouter(
    prefix="/api/inspections",
    tags=["Inspections"],
)


@router.post(
    "",
    response_model=InspectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inspection(
    data: InspectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        inspection = start_inspection(
            db,
            equipment_id=data.equipment_id,
            user_id=current_user.id,
        )
        db.commit()
        db.refresh(inspection)
        return inspection

    except InspectionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )


@router.get("", response_model=list[InspectionResponse])
def list_inspections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.scalars(
        select(Inspection)
        .where(Inspection.user_id == current_user.id)
        .order_by(Inspection.started_at.desc())
    ).all()


@router.get(
    "/{inspection_id}",
    response_model=InspectionResponse,
)
def get_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = db.scalar(
        select(Inspection).where(
            Inspection.id == inspection_id,
            Inspection.user_id == current_user.id,
        )
    )

    if inspection is None:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found.",
        )

    return inspection


def change_inspection_status(
    inspection_id: int,
    user_id: int,
    final_status: str,
    db: Session,
):
    try:
        inspection = finish_inspection(
            db,
            inspection_id=inspection_id,
            user_id=user_id,
            final_status=final_status,
        )
        db.commit()
        db.refresh(inspection)
        return inspection

    except InspectionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )


@router.post(
    "/{inspection_id}/complete",
    response_model=InspectionResponse,
)
def complete_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return change_inspection_status(
        inspection_id,
        current_user.id,
        "completed",
        db,
    )


@router.post(
    "/{inspection_id}/cancel",
    response_model=InspectionResponse,
)
def cancel_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return change_inspection_status(
        inspection_id,
        current_user.id,
        "cancelled",
        db,
    )
