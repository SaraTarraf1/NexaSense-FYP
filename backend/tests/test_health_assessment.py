from datetime import datetime, timedelta, timezone

import pytest

from app.models.fault_classification import FaultClassification
from app.models.sensor_reading import SensorReading
from app.services.health_assessment_service import assess_equipment_health


ASSESSMENT_TIME = datetime(2026, 11, 26, 10, tzinfo=timezone.utc)


def measurement(reading_id, **overrides):
    values = {
        "id": reading_id,
        "equipment_id": 1,
        "inspection_id": 1,
        "value": 35.0,
        "timestamp": ASSESSMENT_TIME,
        "validation_status": "valid",
        "detection_status": "normal",
        "anomaly_type": None,
    }
    return SensorReading(**(values | overrides))


def assess(readings, classifications=()):
    return assess_equipment_health(
        equipment_type="Air conditioner",
        equipment_id=1,
        inspection_id=1,
        assessed_at=ASSESSMENT_TIME,
        readings=readings,
        classifications=classifications,
    )


def fault(reading_id, evidence_ids, rule_id="DR-001", fault_type="overheating", **overrides):
    values = {
        "source_reading_id": reading_id,
        "status": "identified",
        "matches": [{
            "rule_id": rule_id,
            "fault_type": fault_type,
            "evidence_reading_ids": evidence_ids,
        }],
        "classified_at": ASSESSMENT_TIME,
    }
    return FaultClassification(**(values | overrides))


def test_normal_uses_latest_observations_and_ignores_old_faults():
    older = measurement(1, detection_status="anomaly", anomaly_type="above_threshold")
    readings = [
        ("temperature", older),
        ("temperature", measurement(4)),
        ("vibration", measurement(2, value=2.0)),
        ("thermal", measurement(3, value=50.0)),
    ]
    result = assess(readings, [fault(1, [1, 3])])
    assert result.status == "normal"
    assert result.evidence_reading_ids == (4, 2, 3)
    assert result.fault_rule_ids == ()


def test_critical_has_precedence_and_keeps_matching_rule_ids():
    anomaly = {"detection_status": "anomaly", "anomaly_type": "above_threshold"}
    readings = [
        ("temperature", measurement(1, value=90.0, **anomaly)),
        ("vibration", measurement(2, value=20.0, **anomaly)),
        ("thermal", measurement(3, value=145.0, **anomaly)),
    ]
    result = assess(readings, [
        fault(1, [2, 1], "DR-002", "mechanical_stress"),
        fault(3, [1, 3]),
    ])
    assert result.status == "critical"
    assert result.evidence_reading_ids == (1, 2, 3)
    assert result.fault_rule_ids == ("DR-001", "DR-002")


@pytest.mark.parametrize("with_fault", [False, True])
def test_anomaly_or_mechanical_stress_yields_warning(with_fault):
    anomaly = {"detection_status": "anomaly", "anomaly_type": "above_threshold"}
    readings = [
        ("temperature", measurement(1, value=90.0, **anomaly)),
        ("vibration", measurement(2, value=20.0, **anomaly)),
        ("thermal", measurement(3, value=50.0)),
    ]
    classifications = [fault(1, [2, 1], "DR-002", "mechanical_stress")] if with_fault else []
    result = assess(readings, classifications)
    assert result.status == "warning"
    assert result.fault_rule_ids == (("DR-002",) if with_fault else ())


def test_older_supporting_reading_cannot_escalate_a_newer_snapshot():
    anomaly = {"detection_status": "anomaly", "anomaly_type": "above_threshold"}
    readings = [
        ("temperature", measurement(1, value=90.0, **anomaly)),
        ("vibration", measurement(2, value=2.0)),
        ("thermal", measurement(3, value=145.0, **anomaly)),
        ("thermal", measurement(4, value=50.0)),
    ]
    result = assess(readings, [fault(1, [1, 3])])
    assert result.status == "warning"
    assert result.fault_rule_ids == ()


@pytest.mark.parametrize("overrides", [
    {"equipment_id": 2},
    {"inspection_id": 2},
    {"timestamp": ASSESSMENT_TIME - timedelta(seconds=16)},
    {"timestamp": ASSESSMENT_TIME + timedelta(seconds=1)},
    {"validation_status": "invalid", "detection_status": "not_evaluated"},
    {"detection_status": "not_evaluated"},
])
def test_unusable_observations_yield_insufficient_data(overrides):
    result = assess([
        ("temperature", measurement(1)),
        ("vibration", measurement(2, value=2.0)),
        ("thermal", measurement(3, **overrides)),
    ])
    assert result.status == "insufficient_data"
    assert result.missing_sensor_types == ("thermal",)
    assert result.evidence_reading_ids == (1, 2)


def test_latest_missing_observation_is_not_hidden_by_an_earlier_valid_reading():
    result = assess([
        ("temperature", measurement(1)),
        ("vibration", measurement(2, value=2.0)),
        ("thermal", measurement(3, value=50.0)),
        ("thermal", measurement(4, value=None, validation_status="missing", detection_status="not_evaluated")),
    ])
    assert result.status == "insufficient_data"
    assert result.missing_sensor_types == ("thermal",)


def test_accepts_readings_at_the_freshness_boundary():
    boundary = ASSESSMENT_TIME.replace(tzinfo=None) - timedelta(seconds=15)
    result = assess([
        ("temperature", measurement(1, timestamp=boundary)),
        ("vibration", measurement(2, value=2.0, timestamp=boundary)),
        ("thermal", measurement(3, value=50.0, timestamp=boundary)),
    ])
    assert result.status == "normal"
