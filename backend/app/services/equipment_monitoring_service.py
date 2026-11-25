from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.services.sensor_configuration import (
    SENSOR_DEFINITIONS,
    get_required_sensor_types,
)


RECENT_ANOMALY_LIMIT = 50
RECENT_FAULT_LIMIT = 50


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
            query = select(SensorReading).where(
                SensorReading.equipment_id == equipment.id,
                SensorReading.sensor_id == sensor.id,
                SensorReading.validation_status == "valid",
            )

            # During live monitoring, only use readings
            # belonging to the current active inspection.
            if is_live:
                query = query.where(
                    SensorReading.inspection_id == inspection.id
                )

            latest_valid = db.scalar(
                query.order_by(
                    SensorReading.timestamp.desc(),
                    SensorReading.id.desc(),
                ).limit(1)
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

    anomalies = []
    if is_live:
        anomaly_rows = db.execute(
            select(SensorReading, Sensor.sensor_type)
            .join(Sensor, Sensor.id == SensorReading.sensor_id)
            .where(
                SensorReading.equipment_id == equipment.id,
                SensorReading.inspection_id == inspection.id,
                SensorReading.detection_status == "anomaly",
            )
            .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
            .limit(RECENT_ANOMALY_LIMIT)
        )
        anomalies = [
            {
                **_reading_details(reading, sensor_type),
                "anomaly_type": reading.anomaly_type,
                "message": reading.detection_message,
            }
            for reading, sensor_type in anomaly_rows
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
        "anomalies": anomalies,
        "faults": (
            _get_inspection_faults(db, equipment.id, inspection.id) if inspection else []
        ),
        "health_status": "not_evaluated",
    }


def _reading_details(reading: SensorReading, sensor_type: str) -> dict:
    return {
        "reading_id": reading.id,
        "sensor_type": sensor_type,
        "value": reading.value,
        "unit": reading.unit,
        "timestamp": reading.timestamp,
    }


def _get_inspection_faults(db: Session, equipment_id: int, inspection_id: int) -> list[dict]:
    rows = db.execute(
        select(FaultClassification, SensorReading, Sensor.sensor_type)
        .join(SensorReading, SensorReading.id == FaultClassification.source_reading_id)
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(
            SensorReading.equipment_id == equipment_id,
            SensorReading.inspection_id == inspection_id,
        )
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .limit(RECENT_FAULT_LIMIT)
    ).all()
    evidence_ids = {
        reading_id
        for fault, _, _ in rows
        for match in fault.matches
        for reading_id in match["evidence_reading_ids"]
    }
    evidence = {}
    if evidence_ids:
        evidence_rows = db.execute(
            select(SensorReading, Sensor.sensor_type)
            .join(Sensor, Sensor.id == SensorReading.sensor_id)
            .where(
                SensorReading.id.in_(evidence_ids),
                SensorReading.equipment_id == equipment_id,
                SensorReading.inspection_id == inspection_id,
            )
        )
        evidence = {
            reading.id: _reading_details(reading, sensor_type)
            for reading, sensor_type in evidence_rows
        }

    return [
        {
            "source_reading": _reading_details(reading, sensor_type),
            "status": fault.status,
            "message": fault.message,
            "matches": [
                {
                    **match,
                    "evidence": [
                        evidence[reading_id]
                        for reading_id in match["evidence_reading_ids"]
                        if reading_id in evidence
                    ],
                }
                for match in fault.matches
            ],
            "missing_sensor_types": fault.missing_sensor_types,
        }
        for fault, reading, sensor_type in rows
    ]