from datetime import datetime, timedelta, timezone

import pytest

from app.models.sensor_reading import SensorReading
from app.services.fault_classification_service import classify_fault


READING_TIME = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)


def reading(reading_id, **overrides):
    values = {
        "id": reading_id,
        "equipment_id": 1,
        "inspection_id": 1,
        "value": 90.0,
        "timestamp": READING_TIME,
        "validation_status": "valid",
        "detection_status": "anomaly",
        "anomaly_type": "above_threshold",
    }
    values.update(overrides)
    return SensorReading(**values)


def test_identified_returns_each_matching_rule_and_its_evidence():
    result = classify_fault(
        "Air conditioner",
        "temperature",
        reading(1),
        [
            ("thermal", reading(2, value=145.0)),
            ("vibration", reading(3, value=20.0)),
        ],
    )

    assert result.status == "identified"
    assert [(match.rule_id, match.fault_type, match.evidence_reading_ids) for match in result.matches] == [
        ("DR-001", "overheating", (1, 2)),
        ("DR-002", "mechanical_stress", (3, 1)),
    ]


def test_matching_rule_is_reported_when_another_rule_lacks_support():
    result = classify_fault(
        "Air conditioner", "temperature", reading(1), [("thermal", reading(2, value=145.0))]
    )

    assert result.status == "identified"
    assert [match.rule_id for match in result.matches] == ["DR-001"]


def test_latest_supporting_reading_supersedes_an_older_anomaly():
    result = classify_fault(
        "Electrical panel",
        "temperature",
        reading(1),
        [
            ("thermal", reading(3, value=50.0, detection_status="normal", anomaly_type=None)),
            ("thermal", reading(2, value=145.0)),
        ],
    )

    assert result.status == "unknown"
    assert result.matches == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"equipment_id": 2},
        {"inspection_id": 2},
        {"timestamp": READING_TIME - timedelta(seconds=16)},
        {"timestamp": READING_TIME + timedelta(seconds=16)},
        {"value": None, "validation_status": "missing", "detection_status": "not_evaluated"},
        {"validation_status": "invalid", "detection_status": "not_evaluated"},
        {"detection_status": "not_evaluated", "anomaly_type": None},
    ],
)
def test_undetermined_ignores_unsuitable_support(overrides):
    result = classify_fault(
        "Electrical panel",
        "temperature",
        reading(1),
        [("thermal", reading(2, **overrides))],
    )

    assert result.status == "undetermined"
    assert result.missing_sensor_types == ("thermal",)


@pytest.mark.parametrize("offset", [-15, 15])
def test_support_within_the_window_includes_the_boundary(offset):
    timestamp = READING_TIME.replace(tzinfo=None) + timedelta(seconds=offset)
    result = classify_fault(
        "Electrical panel",
        "temperature",
        reading(1),
        [("thermal", reading(2, timestamp=timestamp))],
    )

    assert result.status == "identified"
    assert result.matches[0].fault_type == "electrical_overheating"


def test_low_anomaly_with_valid_support_has_no_matching_high_rule():
    result = classify_fault(
        "Electrical panel",
        "temperature",
        reading(1, value=15.0, anomaly_type="below_threshold"),
        [("thermal", reading(2, value=145.0))],
    )

    assert result.status == "unknown"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"detection_status": "normal", "anomaly_type": None}, "skipped"),
        ({"validation_status": "invalid"}, "data_error"),
        ({"value": None, "validation_status": "missing"}, "data_error"),
        ({"detection_status": "not_evaluated"}, "data_error"),
        ({"anomaly_type": None}, "data_error"),
    ],
)
def test_source_measurement_controls_whether_classification_runs(overrides, expected):
    result = classify_fault("Air conditioner", "temperature", reading(1, **overrides), ())

    assert result.status == expected
    assert result.matches == ()
