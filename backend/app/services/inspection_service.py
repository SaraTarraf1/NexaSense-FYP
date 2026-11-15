
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.services.sensor_configuration import get_required_sensor_types


class InspectionError(Exception):
    """An inspection cannot be started or updated."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


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

    existing = db.scalar(
        select(Inspection).where(
            Inspection.equipment_id == equipment_id,
            Inspection.status == "active",
        )
    )

    if existing is not None:
        raise InspectionError(
            "This equipment already has an active inspection.", 409
        )

    required_types = get_required_sensor_types(
        equipment.equipment_type
    )

    if not required_types:
        raise InspectionError(
            "No sensor configuration exists for this equipment type.",
            422,
        )

    available_sensors = db.scalars(
        select(Sensor).where(
            Sensor.sensor_type.in_(required_types),
            Sensor.is_active.is_(True),
        )
    ).all()

    available_types = {
        sensor.sensor_type for sensor in available_sensors
    }

    missing_types = [
        sensor_type
        for sensor_type in required_types
        if sensor_type not in available_types
    ]

    if missing_types:
        raise InspectionError(
            "Required sensors unavailable: "
            + ", ".join(missing_types),
            409,
        )

    inspection = Inspection(
        equipment_id=equipment.id,
        user_id=user_id,
        status="active",
    )

    db.add(inspection)
    db.flush()

    return inspection


def finish_inspection(
    db: Session,
    inspection_id: int,
    user_id: int,
    final_status: str,
) -> Inspection:
    """
    Complete or cancel an active inspection.

    The caller is responsible for committing the transaction.
    """

    if final_status not in {"completed", "cancelled"}:
        raise InspectionError("Invalid final inspection status.")

    inspection = db.scalar(
        select(Inspection)
        .where(
            Inspection.id == inspection_id,
            Inspection.user_id == user_id,
        )
        .with_for_update()
    )

    if inspection is None:
        raise InspectionError("Inspection not found.", 404)

    if inspection.status != "active":
        raise InspectionError(
            "This inspection is no longer active.", 409
        )

    inspection.status = final_status
    inspection.ended_at = datetime.now(timezone.utc)

    db.flush()

    return inspection
