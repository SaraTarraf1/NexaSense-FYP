
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.services.sensor_configuration import (
    SENSOR_DEFINITIONS,
    get_required_sensor_types,
)


def get_equipment_monitoring(
    db: Session,
    equipment: Equipment,
) -> dict:
    now = datetime.now(timezone.utc)

    inspection = db.scalar(
        select(Inspection)
        .where(Inspection.equipment_id == equipment.id)
        .order_by(
            Inspection.started_at.desc(),
            Inspection.id.desc(),
        )
        .limit(1)
    )

    is_live = (
        inspection is not None
        and inspection.status == "active"
    )

    required_types = get_required_sensor_types(
        equipment.equipment_type
    )

    sensors = []

    for sensor_type in required_types:
        sensor = db.scalar(
            select(Sensor).where(
                Sensor.sensor_type == sensor_type
            )
        )

        default_interval = SENSOR_DEFINITIONS.get(
            sensor_type, {}
        ).get("collection_interval_seconds", 5)

        interval = (
            sensor.collection_interval_seconds
            if sensor is not None
            else default_interval
        )

        threshold = interval * 3

        latest_valid = None

        if sensor is not None:
            latest_valid = db.scalar(
                select(SensorReading)
                .where(
                    SensorReading.equipment_id == equipment.id,
                    SensorReading.sensor_id == sensor.id,
                    SensorReading.validation_status == "valid",
                )
                .order_by(
                    SensorReading.timestamp.desc(),
                    SensorReading.id.desc(),
                )
                .limit(1)
            )

        if latest_valid is None:
            sensor_status = "missing"
        else:
            timestamp = latest_valid.timestamp

            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(
                    tzinfo=timezone.utc
                )

            age_seconds = (
                now - timestamp
            ).total_seconds()

            sensor_status = (
                "current"
                if is_live and age_seconds <= threshold
                else "stale"
            )

        sensors.append({
            "sensor_type": sensor_type,
            "unit": (
                sensor.unit
                if sensor is not None
                else SENSOR_DEFINITIONS.get(
                    sensor_type, {}
                ).get("unit")
            ),
            "value": (
                latest_valid.value
                if latest_valid is not None
                else None
            ),
            "timestamp": (
                latest_valid.timestamp
                if latest_valid is not None
                else None
            ),
            "validation_status": (
                latest_valid.validation_status
                if latest_valid is not None
                else None
            ),
            "status": sensor_status,
            "freshness_threshold_seconds": threshold,
        })

    statuses = {item["status"] for item in sensors}

    if not sensors or "missing" in statuses:
        monitoring_status = "missing"
    elif "stale" in statuses:
        monitoring_status = "stale"
    else:
        monitoring_status = "current"

    timestamps = [
        item["timestamp"]
        for item in sensors
        if item["timestamp"] is not None
    ]

    return {
        "equipment_id": equipment.id,
        "equipment_name": equipment.name,
        "equipment_type": equipment.equipment_type,
        "equipment_status": equipment.status,
        "inspection_id": (
            inspection.id if inspection else None
        ),
        "inspection_status": (
            inspection.status if inspection else None
        ),
        "monitoring_status": monitoring_status,
        "is_live": is_live,
        "sensors": sensors,
        "last_valid_reading_at": (
            max(timestamps) if timestamps else None
        ),
        "anomalies": [],
        "faults": [],
        "health_status": "not_evaluated",
    }
