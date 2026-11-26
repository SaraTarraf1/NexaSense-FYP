from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.alert_notification import AlertNotification
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor_reading import SensorReading
from app.services.alert_configuration import (
    ALERT_DUPLICATE_WINDOW,
    HEALTH_ALERT_SEVERITIES,
    IN_APP_NOTIFICATION_CHANNEL,
    AlertEventType,
    AlertSeverity,
    get_anomaly_alert_severity,
    get_fault_alert_severity,
)


@dataclass(frozen=True)
class AlertCandidate:
    source_reading_id: int
    event_type: AlertEventType
    event_key: str
    severity: AlertSeverity
    description: str
    evidence_reading_ids: list[int]


def _anomaly_candidates(
    readings: list[SensorReading], sensor_types: dict[int, str]
) -> Iterator[AlertCandidate]:
    for reading in readings:
        severity = get_anomaly_alert_severity(reading.validation_status, reading.detection_status)
        if severity is None:
            continue

        sensor_type = sensor_types[reading.sensor_id]
        direction = reading.anomaly_type or "outside_threshold"
        yield AlertCandidate(
            source_reading_id=reading.id,
            event_type="anomaly",
            event_key=f"anomaly:{sensor_type}:{direction}",
            severity=severity,
            description=(
                f"{sensor_type.replace('_', ' ').capitalize()} reading of "
                f"{reading.value} {reading.unit} is outside its configured operating range."
            ),
            evidence_reading_ids=[reading.id],
        )


def _fault_candidates(classifications: list[FaultClassification]) -> Iterator[AlertCandidate]:
    for classification in classifications:
        if classification.status == "identified":
            for match in classification.matches:
                fault_type = match["fault_type"]
                severity = get_fault_alert_severity(classification.status, fault_type)
                if severity is None:
                    continue

                rule_id = match["rule_id"]
                yield AlertCandidate(
                    source_reading_id=classification.source_reading_id,
                    event_type="fault",
                    event_key=f"fault:{rule_id}",
                    severity=severity,
                    description=f"Potential {fault_type.replace('_', ' ')} (rule {rule_id}).",
                    evidence_reading_ids=match["evidence_reading_ids"],
                )
            continue

        severity = get_fault_alert_severity(classification.status)
        if severity is not None:
            description = classification.message
            if classification.missing_sensor_types:
                missing = ", ".join(classification.missing_sensor_types)
                description = f"{description} Needed readings: {missing}."
            yield AlertCandidate(
                source_reading_id=classification.source_reading_id,
                event_type="fault",
                event_key=f"fault:{classification.status}",
                severity=severity,
                description=description,
                evidence_reading_ids=[classification.source_reading_id],
            )


def _health_candidates(assessment: EquipmentHealthAssessment | None) -> Iterator[AlertCandidate]:
    if assessment is None:
        return

    severity = HEALTH_ALERT_SEVERITIES.get(assessment.status)
    if severity is not None:
        yield AlertCandidate(
            source_reading_id=assessment.trigger_reading_id,
            event_type="health",
            event_key=f"health:{assessment.status}",
            severity=severity,
            description=f"Equipment health is {assessment.status}. {assessment.message}",
            evidence_reading_ids=assessment.evidence_reading_ids,
        )


def record_collection_alerts(
    db: Session,
    *,
    equipment: Equipment,
    inspection: Inspection,
    readings: list[SensorReading],
    sensor_types: dict[int, str],
    classifications: list[FaultClassification],
    now: datetime,
    health_assessment: EquipmentHealthAssessment | None = None,
) -> None:
    """Save alerts and pending notifications while collection holds the inspection lock."""
    candidates = [
        *_anomaly_candidates(readings, sensor_types),
        *_fault_candidates(classifications),
        *_health_candidates(health_assessment),
    ]
    if not candidates:
        return

    related_reading_ids = {candidate.source_reading_id for candidate in candidates}
    related_reading_ids.update(
        reading_id for candidate in candidates for reading_id in candidate.evidence_reading_ids
    )
    within_window = Alert.created_at > now - ALERT_DUPLICATE_WINDOW
    existing = db.execute(
        select(
            Alert.source_reading_id, Alert.event_key, Alert.evidence_reading_ids, within_window
        ).where(
            Alert.equipment_id == equipment.id,
            Alert.inspection_id == inspection.id,
            Alert.event_key.in_({candidate.event_key for candidate in candidates}),
            or_(
                within_window,
                Alert.source_reading_id.in_(related_reading_ids),
            ),
        )
    ).all()
    recent_keys = {key for _, key, _, recent in existing if recent}
    saved_triggers = {(reading_id, key) for reading_id, key, _, _ in existing}
    saved_evidence = {
        (key, tuple(sorted(reading_ids))) for _, key, reading_ids, _ in existing
    }

    selected = []
    for candidate in candidates:
        if (
            candidate.event_key in recent_keys
            or (candidate.source_reading_id, candidate.event_key) in saved_triggers
            or (candidate.event_key, tuple(sorted(candidate.evidence_reading_ids))) in saved_evidence
        ):
            continue

        selected.append(candidate)
        recent_keys.add(candidate.event_key)

    if not selected:
        return

    # Persist the fault and health sources before adding alerts that reference them.
    db.flush()
    alerts = [
        Alert(
            equipment_id=equipment.id,
            inspection_id=inspection.id,
            source_reading_id=candidate.source_reading_id,
            fault_classification_id=(
                candidate.source_reading_id if candidate.event_type == "fault" else None
            ),
            health_assessment_id=(
                health_assessment.id
                if candidate.event_type == "health" and health_assessment is not None
                else None
            ),
            event_type=candidate.event_type,
            event_key=candidate.event_key,
            severity=candidate.severity,
            description=candidate.description,
            evidence_reading_ids=candidate.evidence_reading_ids,
            created_at=now,
        )
        for candidate in selected
    ]
    db.add_all(alerts)
    db.flush()
    db.add_all(
        AlertNotification(
            alert_id=alert.id,
            recipient_user_id=equipment.user_id,
            channel=IN_APP_NOTIFICATION_CHANNEL,
        )
        for alert in alerts
    )
