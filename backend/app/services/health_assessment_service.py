from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.services.alert_configuration import get_fault_alert_severity
from app.services.sensor_configuration import get_required_sensor_types
from app.services.sensor_validation import is_evaluated_measurement


HEALTH_READING_MAX_AGE = timedelta(seconds=15)
HealthStatus = Literal["normal", "warning", "critical", "insufficient_data"]


@dataclass(frozen=True)
class HealthAssessmentResult:
    status: HealthStatus
    message: str
    evidence_reading_ids: tuple[int, ...] = ()
    fault_rule_ids: tuple[str, ...] = ()
    missing_sensor_types: tuple[str, ...] = ()


def _with_timezone(timestamp: datetime) -> datetime:
    return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp


def assess_equipment_health(
    *,
    equipment_type: str,
    equipment_id: int,
    inspection_id: int,
    assessed_at: datetime,
    readings: Iterable[tuple[str, SensorReading]],
    classifications: Iterable[FaultClassification] = (),
) -> HealthAssessmentResult:
    """Assess health from the latest sensor observations within one inspection."""
    required = get_required_sensor_types(equipment_type)
    if not required:
        return HealthAssessmentResult(
            "insufficient_data", "No sensors are configured for this equipment category."
        )

    assessed_at = _with_timezone(assessed_at)
    latest: dict[str, tuple[datetime, SensorReading]] = {}
    for sensor_type, reading in readings:
        if (
            sensor_type not in required
            or reading.equipment_id != equipment_id
            or reading.inspection_id != inspection_id
            or reading.id is None
            or reading.timestamp is None
        ):
            continue

        timestamp = _with_timezone(reading.timestamp)
        current = latest.get(sensor_type)
        if timestamp <= assessed_at and (
            current is None or (timestamp, reading.id) > (current[0], current[1].id)
        ):
            latest[sensor_type] = (timestamp, reading)

    fresh = {
        sensor_type: reading
        for sensor_type, (timestamp, reading) in latest.items()
        if assessed_at - timestamp <= HEALTH_READING_MAX_AGE
        and is_evaluated_measurement(reading)
    }
    evidence_ids = tuple(fresh[sensor_type].id for sensor_type in required if sensor_type in fresh)
    missing = tuple(sensor_type for sensor_type in required if sensor_type not in fresh)
    if missing:
        return HealthAssessmentResult(
            "insufficient_data",
            "Current valid readings are required from all configured sensors.",
            evidence_reading_ids=evidence_ids,
            missing_sensor_types=missing,
        )

    current_ids = set(evidence_ids)
    current_matches = [
        match
        for classification in classifications
        if classification.status == "identified"
        and classification.source_reading_id in current_ids
        and (
            classification.classified_at is None
            or _with_timezone(classification.classified_at) <= assessed_at
        )
        for match in classification.matches
        if classification.source_reading_id in match["evidence_reading_ids"]
        and current_ids.issuperset(match["evidence_reading_ids"])
    ]
    fault_rule_ids = tuple(sorted({match["rule_id"] for match in current_matches}))
    if any(
        get_fault_alert_severity("identified", match["fault_type"]) == "critical"
        for match in current_matches
    ):
        return HealthAssessmentResult(
            "critical", "Current readings support a critical fault rule.",
            evidence_ids, fault_rule_ids,
        )
    if current_matches or any(reading.detection_status == "anomaly" for reading in fresh.values()):
        return HealthAssessmentResult(
            "warning", "Current readings show an anomaly or a warning-level fault.",
            evidence_ids, fault_rule_ids,
        )
    return HealthAssessmentResult(
        "normal", "All required sensor readings are current and within their operating ranges.",
        evidence_ids,
    )


def record_health_assessment(
    db: Session,
    *,
    equipment: Equipment,
    inspection: Inspection,
    trigger_reading: SensorReading,
) -> EquipmentHealthAssessment:
    """Record one assessment while collection holds the inspection lock."""
    db.flush()
    assessed_at = datetime.now(timezone.utc)
    rows = db.execute(
        select(Sensor.sensor_type, SensorReading)
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(
            SensorReading.equipment_id == equipment.id,
            SensorReading.inspection_id == inspection.id,
            SensorReading.timestamp.between(assessed_at - HEALTH_READING_MAX_AGE, assessed_at),
            Sensor.is_active.is_(True),
        )
    )
    readings = [(sensor_type, reading) for sensor_type, reading in rows]
    classifications = db.scalars(
        select(FaultClassification).where(
            FaultClassification.source_reading_id.in_([reading.id for _, reading in readings])
        )
    )
    result = assess_equipment_health(
        equipment_type=equipment.equipment_type,
        equipment_id=equipment.id,
        inspection_id=inspection.id,
        assessed_at=assessed_at,
        readings=readings,
        classifications=classifications,
    )
    assessment = EquipmentHealthAssessment(
        equipment_id=equipment.id,
        inspection_id=inspection.id,
        trigger_reading_id=trigger_reading.id,
        status=result.status,
        message=result.message,
        assessed_at=assessed_at,
        evidence_reading_ids=list(result.evidence_reading_ids),
        fault_rule_ids=list(result.fault_rule_ids),
        missing_sensor_types=list(result.missing_sensor_types),
    )
    db.add(assessment)
    return assessment
