
from datetime import datetime, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.services.sensor_configuration import get_required_sensor_types


class InspectionError(Exception):
    """An inspection request conflicts with the current state."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _lock_owned_active_equipment(db: Session, equipment_id: int, user_id: int) -> Equipment:
    # Lock the equipment row to serialize inspection starts
    # for the same equipment.
    equipment = db.scalar(
        select(Equipment)
        .where(
            Equipment.id == equipment_id,
            Equipment.user_id == user_id,
        )
        .with_for_update()
    )

    if equipment is None:
        raise InspectionError("Equipment not found.", 404)

    if equipment.status != "active":
        raise InspectionError(
            "Only active equipment can be inspected.", 409
        )

    return equipment


def _start_blocker(
    equipment: Equipment, has_active_inspection: bool, available_types: set[str]
) -> InspectionError | None:
    if equipment.status != "active":
        return InspectionError("Only active equipment can be inspected.", 409)
    if has_active_inspection:
        return InspectionError(
            "Another inspection is running on this equipment. End it before starting this one.",
            409,
        )

    required_types = get_required_sensor_types(equipment.equipment_type)
    if not required_types:
        return InspectionError("No sensor configuration exists for this equipment type.", 422)

    missing_types = [kind for kind in required_types if kind not in available_types]
    if missing_types:
        return InspectionError("Required sensors unavailable: " + ", ".join(missing_types), 409)
    return None


def inspection_start_blockers(
    db: Session, equipment_ids: set[int]
) -> dict[int, InspectionError]:
    if not equipment_ids:
        return {}

    equipment = db.scalars(select(Equipment).where(Equipment.id.in_(equipment_ids))).all()
    active_ids = set(db.scalars(
        select(Inspection.equipment_id).where(
            Inspection.equipment_id.in_(equipment_ids), Inspection.status == "active"
        )
    ))
    available_types = set(db.scalars(select(Sensor.sensor_type).where(Sensor.is_active.is_(True))))
    blockers = {}
    for item in equipment:
        blocker = _start_blocker(item, item.id in active_ids, available_types)
        if blocker is not None:
            blockers[item.id] = blocker
    return blockers


def _ensure_can_start(db: Session, equipment: Equipment) -> None:
    blocker = inspection_start_blockers(db, {equipment.id}).get(equipment.id)
    if blocker is not None:
        raise blocker


def record_due_inspection_reminders(db: Session) -> None:
    now = datetime.now(timezone.utc)
    due = (
        Inspection.status == "scheduled",
        Inspection.scheduled_at <= now,
        Inspection.ready_reminded_at.is_(None),
    )
    candidates = db.execute(select(Inspection.id, Inspection.equipment_id).where(*due)).all()
    blockers = inspection_start_blockers(db, {item.equipment_id for item in candidates})
    ready_ids = [item.id for item in candidates if item.equipment_id not in blockers]
    if ready_ids:
        db.execute(
            update(Inspection)
            .where(Inspection.id.in_(ready_ids), *due)
            .values(ready_reminded_at=now)
        )


def start_inspection(
    db: Session,
    equipment_id: int,
    user_id: int,
) -> Inspection:
    """
    Start an inspection for equipment owned by the user.

    Required sensors are selected automatically.
    The caller is responsible for committing the transaction.
    """

    equipment = _lock_owned_active_equipment(db, equipment_id, user_id)
    _ensure_can_start(db, equipment)

    inspection = Inspection(
        equipment_id=equipment.id,
        user_id=user_id,
        status="active",
    )

    db.add(inspection)
    db.flush()

    return inspection


def schedule_inspection(
    db: Session,
    equipment_id: int,
    user_id: int,
    scheduled_at: datetime,
    notes: str | None = None,
) -> Inspection:
    equipment = _lock_owned_active_equipment(db, equipment_id, user_id)
    if scheduled_at.utcoffset() is None:
        raise InspectionError("Schedule time must include a time zone.", 422)

    scheduled_at = scheduled_at.astimezone(timezone.utc)
    if scheduled_at <= datetime.now(timezone.utc):
        raise InspectionError("Schedule time must be in the future.", 422)

    conflict = db.scalar(
        select(Inspection.id).where(
            Inspection.equipment_id == equipment.id,
            Inspection.scheduled_at == scheduled_at,
            or_(Inspection.status != "cancelled", Inspection.started_at.is_not(None)),
        )
    )
    if conflict is not None:
        raise InspectionError(
            f"{equipment.name} already has an inspection booked for that time. Choose another time.",
            409,
        )

    inspection = Inspection(
        equipment_id=equipment.id,
        user_id=user_id,
        status="scheduled",
        scheduled_at=scheduled_at,
        started_at=None,
        notes=(notes.strip() or None) if notes is not None else None,
    )
    db.add(inspection)
    db.flush()
    return inspection


def start_scheduled_inspection(db: Session, inspection_id: int, user_id: int) -> Inspection:
    owned_inspection = select(Inspection).where(
        Inspection.id == inspection_id, Inspection.user_id == user_id
    )
    equipment_id = db.scalar(owned_inspection.with_only_columns(Inspection.equipment_id))
    if equipment_id is None:
        raise InspectionError("Inspection not found.", 404)

    equipment = _lock_owned_active_equipment(db, equipment_id, user_id)
    inspection = db.scalar(owned_inspection.with_for_update())
    if inspection is None:
        raise InspectionError("Inspection not found.", 404)
    if inspection.status != "scheduled" or inspection.scheduled_at is None:
        raise InspectionError("Only scheduled inspections can be started here.", 409)

    scheduled_at = inspection.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if scheduled_at > now:
        raise InspectionError("This inspection cannot start before its scheduled time.", 409)

    _ensure_can_start(db, equipment)
    inspection.status = "active"
    inspection.started_at = now
    db.flush()
    return inspection


def finish_inspection(
    db: Session,
    inspection_id: int,
    user_id: int,
    final_status: str,
    failure_reason: str | None = None,
    *,
    expected_status: str = "active",
) -> Inspection:
    """
    Record an inspection outcome if it is still in the expected state.

    The caller is responsible for committing the transaction.
    """

    if final_status not in {"completed", "cancelled", "failed"}:
        raise InspectionError("Invalid final inspection status.")

    inspection = db.scalar(
        select(Inspection)
        .where(
            Inspection.id == inspection_id,
            Inspection.user_id == user_id,
            Inspection.equipment_id.in_(select(Equipment.id).where(Equipment.user_id == user_id)),
        )
        .with_for_update()
    )

    if inspection is None:
        raise InspectionError("Inspection not found.", 404)

    if inspection.status != expected_status:
        raise InspectionError(f"This inspection is no longer {expected_status}.", 409)

    inspection.status = final_status
    inspection.ended_at = datetime.now(timezone.utc)
    if final_status == "failed" and failure_reason is not None:
        inspection.failure_reason = failure_reason.strip() or None

    db.flush()

    return inspection
