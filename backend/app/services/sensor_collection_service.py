
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading

from app.services.sensor_configuration import (
    get_required_sensor_types,
)
from app.services.sensor_simulator import (
    simulate_sensor_reading,
)
from app.services.sensor_reading_service import (
    save_sensor_reading,
)


def collect_inspection_readings(
    db: Session,
    inspection_id: int,
) -> list[SensorReading]:
    """
    Collect readings for all required sensors that are due.

    The caller controls the database transaction.
    Only active inspections can collect measurements.
    """

    # Lock the inspection row so collection cannot overlap
    # with completion or cancellation.
    inspection = db.scalar(
        select(Inspection)
        .where(Inspection.id == inspection_id)
        .with_for_update()
    )

    if inspection is None:
        raise ValueError("Inspection not found.")

    if inspection.status != "active":
        return []

    equipment = db.get(Equipment, inspection.equipment_id)

    if equipment is None:
        raise ValueError("Inspection equipment not found.")

    required_types = get_required_sensor_types(
        equipment.equipment_type
    )

    sensors = db.scalars(
        select(Sensor).where(
            Sensor.sensor_type.in_(required_types),
            Sensor.is_active.is_(True),
        )
    ).all()

    now = datetime.now(timezone.utc)
    collected = []

    for sensor in sensors:

        latest_timestamp = db.scalar(
            select(SensorReading.timestamp)
            .where(
                SensorReading.inspection_id == inspection.id,
                SensorReading.sensor_id == sensor.id,
            )
            .order_by(SensorReading.timestamp.desc())
            .limit(1)
        )

        if latest_timestamp is not None:
            elapsed = (
                now - latest_timestamp
            ).total_seconds()

            if elapsed < sensor.collection_interval_seconds:
                continue

        measurement = simulate_sensor_reading(
            sensor.sensor_type
        )

        reading = save_sensor_reading(
            db=db,
            inspection_id=inspection.id,
            sensor_type=sensor.sensor_type,
            value=measurement.value,
        )

        collected.append(reading)

    return collected
