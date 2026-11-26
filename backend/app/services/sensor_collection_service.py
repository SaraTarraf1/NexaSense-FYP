
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading

from app.services.alert_service import record_collection_alerts
from app.services.fault_classification_service import (
    SUPPORTING_READING_WINDOW,
    classify_fault,
)
from app.services.health_assessment_service import record_health_assessment
from app.services.sensor_configuration import (
    get_required_sensor_types,
)
from app.services.sensor_simulator import (
    simulate_sensor_reading,
)
from app.services.sensor_reading_service import (
    save_sensor_reading,
)


logger = logging.getLogger(__name__)


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
            if latest_timestamp.tzinfo is None:
                latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
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

    if not collected:
        return collected

    sensor_types = {sensor.id: sensor.sensor_type for sensor in sensors}
    classifications = _record_fault_classifications(
        db, equipment.equipment_type, collected, sensor_types
    )
    assessment = record_health_assessment(
        db, equipment=equipment, inspection=inspection, trigger_reading=collected[-1]
    )
    record_collection_alerts(
        db,
        equipment=equipment,
        inspection=inspection,
        readings=collected,
        sensor_types=sensor_types,
        classifications=classifications,
        now=now,
        health_assessment=assessment,
    )
    return collected


def _record_fault_classifications(
    db: Session,
    equipment_type: str,
    collected: list[SensorReading],
    sensor_types: dict[int, str],
) -> list[FaultClassification]:
    anomalies = [reading for reading in collected if reading.detection_status == "anomaly"]
    if not anomalies:
        return []

    first_timestamp = min(reading.timestamp for reading in anomalies)
    last_timestamp = max(reading.timestamp for reading in collected)
    evidence_rows = db.execute(
        select(Sensor.sensor_type, SensorReading)
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(
            SensorReading.equipment_id == anomalies[0].equipment_id,
            SensorReading.inspection_id == anomalies[0].inspection_id,
            SensorReading.validation_status == "valid",
            SensorReading.timestamp.between(
                first_timestamp - SUPPORTING_READING_WINDOW, last_timestamp
            ),
        )
    )
    evidence = [(kind, candidate) for kind, candidate in evidence_rows]

    classifications = []
    for reading in anomalies:
        result = classify_fault(
            equipment_type, sensor_types[reading.sensor_id], reading, evidence
        )
        if result.status in ("skipped", "data_error"):
            logger.warning(
                "Could not classify anomaly reading %s: %s", reading.id, result.message
            )
            continue

        classification = FaultClassification(
            source_reading_id=reading.id,
            status=result.status,
            message=result.message,
            matches=[
                {
                    "rule_id": match.rule_id,
                    "fault_type": match.fault_type,
                    "evidence_reading_ids": list(match.evidence_reading_ids),
                }
                for match in result.matches
            ],
            missing_sensor_types=list(result.missing_sensor_types),
        )
        db.add(classification)
        classifications.append(classification)

    return classifications
