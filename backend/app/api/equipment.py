
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.auth import get_current_user
from app.core.database import SessionLocal
from app.core.equipment_identifiers import next_identifier
from app.models.equipment import Equipment
from app.models.user import User
from app.schemas.equipment import (
    EquipmentCreate,
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
    response_model=list[EquipmentResponse],
)
def list_equipment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Equipment)
        .where(Equipment.user_id == current_user.id)
        .order_by(Equipment.id.desc())
    )

    return db.scalars(statement).all()


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

    required_fields = {"name", "equipment_type", "location", "identifier"}
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
