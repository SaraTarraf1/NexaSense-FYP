
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.auth import get_current_user
from app.core.database import SessionLocal
from app.core.equipment_identifiers import next_identifier
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentListResponse,
    EquipmentUpdate,
    EquipmentResponse,
)


router = APIRouter(
    prefix="/api/equipment",
    tags=["Equipment"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_identifier(db, user_id, identifier, equipment_id=None):
    query = select(Equipment).where(Equipment.user_id == user_id, Equipment.identifier == identifier)
    if equipment_id is not None:
        query = query.where(Equipment.id != equipment_id)
    if db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail=f"Identifier {identifier} is already used. Choose another identifier.")


def save_equipment(db, equipment):
    try:
        db.commit()
        db.refresh(equipment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This equipment identifier is already used.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Equipment could not be saved. Please try again.") from exc


@router.post(
    "",
    response_model=EquipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_equipment(
    equipment_data: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Serialize registrations for one owner so automatically assigned IDs do not collide.
    db.scalar(select(User).where(User.id == current_user.id).with_for_update())
    identifier = equipment_data.identifier
    if identifier is None:
        used = set(db.scalars(select(Equipment.identifier).where(Equipment.user_id == current_user.id)))
        identifier = next_identifier(equipment_data.equipment_type, used)
    check_identifier(db, current_user.id, identifier)
    equipment = Equipment(
        **equipment_data.model_dump(exclude={"identifier"}),
        identifier=identifier,
        user_id=current_user.id,
    )

    db.add(equipment)
    save_equipment(db, equipment)

    return equipment


@router.get(
    "",
    response_model=list[EquipmentListResponse],
)
def list_equipment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    latest_inspection_id = (
        select(Inspection.id)
        .where(Inspection.equipment_id == Equipment.id, Inspection.started_at.is_not(None))
        .order_by(Inspection.started_at.desc(), Inspection.id.desc())
        .limit(1)
        .correlate(Equipment)
        .scalar_subquery()
    )
    latest_assessment_id = (
        select(EquipmentHealthAssessment.id)
        .where(
            EquipmentHealthAssessment.equipment_id == Equipment.id,
            EquipmentHealthAssessment.inspection_id == Inspection.id,
        )
        .order_by(EquipmentHealthAssessment.assessed_at.desc(), EquipmentHealthAssessment.id.desc())
        .limit(1)
        .correlate(Equipment, Inspection)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Equipment, EquipmentHealthAssessment.status, Inspection.started_at)
        .select_from(Equipment)
        .outerjoin(Inspection, Inspection.id == latest_inspection_id)
        .outerjoin(EquipmentHealthAssessment, EquipmentHealthAssessment.id == latest_assessment_id)
        .where(Equipment.user_id == current_user.id)
        .order_by(Equipment.id.desc())
    )

    return [
        EquipmentListResponse(
            **EquipmentResponse.model_validate(equipment).model_dump(),
            health_status=health_status or "not_evaluated",
            last_inspection_at=last_inspection_at,
        )
        for equipment, health_status, last_inspection_at in rows
    ]


@router.get(
    "/{equipment_id}",
    response_model=EquipmentResponse,
)
def get_equipment(
    equipment_id: int,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found.",
        )

    return equipment


@router.put(
    "/{equipment_id}",
    response_model=EquipmentResponse,
)
def update_equipment(
    equipment_id: int,
    equipment_data: EquipmentUpdate,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found.",
        )

    updates = equipment_data.model_dump(exclude_unset=True)

    required_fields = {"name", "equipment_type", "location", "identifier", "status"}
    for field in required_fields:
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null.",
            )

    if "identifier" in updates:
        check_identifier(db, current_user.id, updates["identifier"], equipment_id)

    for field, value in updates.items():
        setattr(equipment, field, value)

    save_equipment(db, equipment)

    return equipment


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    equipment = db.scalar(select(Equipment).where(
        Equipment.id == equipment_id,
        Equipment.user_id == current_user.id,
    ))
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    try:
        db.delete(equipment)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Equipment could not be deleted. Please try again.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
