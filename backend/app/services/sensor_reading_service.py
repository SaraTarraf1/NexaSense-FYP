
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.services.sensor_validation import validate_sensor_reading


def save_sensor_reading(
    db: Session,
    inspection_id: int,
    sensor_type: str,
    value: float | None,
) -> SensorReading:
    """
    Validate and store one sensor reading.

    The inspection determines the equipment association.
    Invalid and missing readings are recorded but must not
    be passed to the valid-data processing pipeline.

    The caller controls the database transaction.
    """

    inspection = db.get(Inspection, inspection_id)

    if inspection is None:
        raise ValueError("Inspection not found.")

    if inspection.status != "active":
        raise ValueError("Cannot collect readings for an inactive inspection.")

    equipment = db.get(Equipment, inspection.equipment_id)

    if equipment is None:
        raise ValueError("Inspection equipment not found.")

    if equipment.user_id != inspection.user_id:
        raise ValueError("Inspection equipment ownership mismatch.")

    sensor = db.scalar(
        select(Sensor).where(
            Sensor.sensor_type == sensor_type,
            Sensor.is_active.is_(True),
        )
    )

    if sensor is None:
        raise ValueError(f"Active sensor not found: {sensor_type}")

    validation = validate_sensor_reading(sensor, value)

    reading = SensorReading(
        sensor_id=sensor.id,
        equipment_id=inspection.equipment_id,
        inspection_id=inspection.id,
        value=value if isinstance(value, (int, float))
                     and not isinstance(value, bool) else None,
        unit=sensor.unit,
        validation_status=validation.status,
        validation_message=validation.message,
    )

    db.add(reading)
    db.flush()

    return reading


def get_valid_readings(
    db: Session,
    inspection_id: int,
) -> list[SensorReading]:
    """
    Return only validated sensor measurements.
    """

    return list(
        db.scalars(
            select(SensorReading)
            .where(
                SensorReading.inspection_id == inspection_id,
                SensorReading.validation_status == "valid",
            )
            .order_by(SensorReading.timestamp)
        ).all()
    )
