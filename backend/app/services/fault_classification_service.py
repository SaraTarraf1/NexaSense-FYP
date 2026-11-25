from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Literal

from app.models.sensor_reading import SensorReading
from app.services.fault_configuration import get_fault_rules


SUPPORTING_READING_WINDOW = timedelta(seconds=15)

FaultClassificationStatus = Literal[
    "identified", "unknown", "undetermined", "skipped", "data_error"
]


@dataclass(frozen=True)
class FaultMatch:
    rule_id: str
    fault_type: str
    evidence_reading_ids: tuple[int, ...]


@dataclass(frozen=True)
class FaultClassificationResult:
    status: FaultClassificationStatus
    message: str
    matches: tuple[FaultMatch, ...] = ()
    missing_sensor_types: tuple[str, ...] = ()


def _with_timezone(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def _has_evaluated_measurement(reading: SensorReading) -> bool:
    return (
        reading.validation_status == "valid"
        and reading.id is not None
        and reading.equipment_id is not None
        and reading.inspection_id is not None
        and reading.value is not None
        and isfinite(reading.value)
        and reading.timestamp is not None
        and (
            (reading.detection_status == "normal" and reading.anomaly_type is None)
            or (
                reading.detection_status == "anomaly"
                and reading.anomaly_type in ("above_threshold", "below_threshold")
            )
        )
    )


def classify_fault(
    equipment_type: str,
    sensor_type: str,
    reading: SensorReading,
    supporting_readings: Iterable[tuple[str, SensorReading]],
) -> FaultClassificationResult:
    """Classify one evaluated reading using evidence available at the end of collection."""
    if not _has_evaluated_measurement(reading):
        return FaultClassificationResult(
            "data_error", "Source reading is missing, invalid, or unevaluated."
        )
    if reading.detection_status == "normal":
        return FaultClassificationResult("skipped", "Source reading is normal.")

    rules = [
        rule for rule in get_fault_rules(equipment_type)
        if sensor_type in rule.required_high_sensors
    ]
    if not rules:
        return FaultClassificationResult(
            "unknown", "No diagnostic rule is configured for this sensor and equipment type."
        )

    required_sensor_types = {kind for rule in rules for kind in rule.required_high_sensors}
    evidence = {sensor_type: reading}
    source_time = _with_timezone(reading.timestamp)
    for kind, candidate in supporting_readings:
        if (
            kind == sensor_type
            or kind not in required_sensor_types
            or candidate.equipment_id != reading.equipment_id
            or candidate.inspection_id != reading.inspection_id
            or not _has_evaluated_measurement(candidate)
        ):
            continue

        candidate_time = _with_timezone(candidate.timestamp)
        if abs(candidate_time - source_time) > SUPPORTING_READING_WINDOW:
            continue

        current = evidence.get(kind)
        if current is None or (candidate_time, candidate.id) > (
            _with_timezone(current.timestamp), current.id
        ):
            evidence[kind] = candidate

    matches = []
    for rule in rules:
        if all(
            kind in evidence and evidence[kind].anomaly_type == "above_threshold"
            for kind in rule.required_high_sensors
        ):
            matches.append(
                FaultMatch(
                    rule_id=rule.rule_id,
                    fault_type=rule.fault_type,
                    evidence_reading_ids=tuple(
                        evidence[kind].id for kind in rule.required_high_sensors
                    ),
                )
            )

    if matches:
        return FaultClassificationResult(
            "identified",
            "Sensor readings match prototype diagnostic rules.",
            matches=tuple(matches),
        )

    missing = tuple(sorted(required_sensor_types - evidence.keys()))
    if missing:
        return FaultClassificationResult(
            "undetermined",
            "Recent valid supporting readings are missing.",
            missing_sensor_types=missing,
        )

    return FaultClassificationResult("unknown", "No diagnostic rule matched the available readings.")
