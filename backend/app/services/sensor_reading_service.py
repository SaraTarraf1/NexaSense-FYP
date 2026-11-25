
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.services.anomaly_detection_service import detect_anomaly
from app.services.sensor_validation import validate_sensor_reading


def save_sensor_reading(
    db: Session,
    inspection_id: int,
    sensor_type: str,
    value: float | None,
) -> SensorReading:

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
    detection = detect_anomaly(
        equipment_type=equipment.equipment_type,
        sensor_type=sensor.sensor_type,
        value=value,
        validation_status=validation.status,
    )

    reading = SensorReading(
        sensor_id=sensor.id,
        equipment_id=inspection.equipment_id,
        inspection_id=inspection.id,
        value=value if isinstance(value, (int, float))
                     and not isinstance(value, bool) else None,
        unit=sensor.unit,
        validation_status=validation.status,
        validation_message=validation.message,
        detection_status=detection.status,
        anomaly_type=detection.anomaly_type,
        detection_message=detection.message,
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
