
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate,
    InspectionFailure,
    InspectionReminder,
    InspectionResponse,
    InspectionSchedule,
)
from app.services.inspection_service import (
    InspectionError,
    finish_inspection,
    inspection_start_blockers,
    schedule_inspection,
    start_inspection,
    start_scheduled_inspection,
)


router = APIRouter(
    prefix="/api/inspections",
    tags=["Inspections"],
)


def _inspection_response(
    inspection: Inspection, blockers: dict[int, InspectionError]
) -> InspectionResponse:
    response = InspectionResponse.model_validate(inspection)
    blocker = blockers.get(inspection.equipment_id)
    if inspection.status == "scheduled" and blocker is not None:
        response.start_blocker = blocker.message
    return response


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


@router.post("/schedule", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_inspection(
    data: InspectionSchedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        inspection = schedule_inspection(
            db, data.equipment_id, current_user.id, data.scheduled_at, data.notes
        )
        response = _inspection_response(
            inspection, inspection_start_blockers(db, {inspection.equipment_id})
        )
        db.commit()
        return response
    except InspectionError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{inspection_id}/start", response_model=InspectionResponse)
def start_saved_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        inspection = start_scheduled_inspection(db, inspection_id, current_user.id)
        db.commit()
        db.refresh(inspection)
        return inspection
    except InspectionError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=list[InspectionResponse])
def list_inspections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspections = db.scalars(
        select(Inspection)
        .join(Equipment, Equipment.id == Inspection.equipment_id)
        .where(Inspection.user_id == current_user.id, Equipment.user_id == current_user.id)
        .order_by(func.coalesce(Inspection.started_at, Inspection.scheduled_at).desc(), Inspection.id.desc())
    ).all()
    blockers = inspection_start_blockers(
        db, {inspection.equipment_id for inspection in inspections if inspection.status == "scheduled"}
    )
    return [_inspection_response(inspection, blockers) for inspection in inspections]


@router.get("/reminders", response_model=list[InspectionReminder])
def list_inspection_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminders = db.execute(
        select(
            Inspection.equipment_id,
            Inspection.id.label("inspection_id"),
            Equipment.name.label("equipment_name"),
            Inspection.scheduled_at,
            Inspection.ready_reminded_at.label("reminded_at"),
        )
        .join(Equipment, Equipment.id == Inspection.equipment_id)
        .where(
            Inspection.user_id == current_user.id,
            Equipment.user_id == current_user.id,
            Inspection.status == "scheduled",
            Inspection.ready_reminded_at.is_not(None),
        )
        .order_by(Inspection.scheduled_at, Inspection.id)
    ).mappings().all()
    blockers = inspection_start_blockers(db, {reminder["equipment_id"] for reminder in reminders})
    return [
        InspectionReminder.model_validate(reminder)
        for reminder in reminders
        if reminder["equipment_id"] not in blockers
    ]


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
        select(Inspection).join(Equipment, Equipment.id == Inspection.equipment_id).where(
            Inspection.id == inspection_id,
            Inspection.user_id == current_user.id,
            Equipment.user_id == current_user.id,
        )
    )

    if inspection is None:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found.",
        )

    blockers = inspection_start_blockers(
        db, {inspection.equipment_id} if inspection.status == "scheduled" else set()
    )
    return _inspection_response(inspection, blockers)


def change_inspection_status(
    inspection_id: int,
    user_id: int,
    final_status: str,
    db: Session,
    failure_reason: str | None = None,
    *,
    expected_status: str = "active",
):
    try:
        inspection = finish_inspection(
            db,
            inspection_id=inspection_id,
            user_id=user_id,
            final_status=final_status,
            failure_reason=failure_reason,
            expected_status=expected_status,
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


@router.post("/{inspection_id}/cancel-booking", response_model=InspectionResponse)
def cancel_scheduled_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return change_inspection_status(
        inspection_id, current_user.id, "cancelled", db, expected_status="scheduled"
    )


@router.post("/{inspection_id}/fail", response_model=InspectionResponse)
def fail_inspection(
    inspection_id: int,
    data: InspectionFailure | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return change_inspection_status(
        db=db,
        inspection_id=inspection_id,
        user_id=current_user.id,
        final_status="failed",
        failure_reason=data.failure_reason if data is not None else None,
    )
