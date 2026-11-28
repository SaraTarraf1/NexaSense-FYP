from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.alerts import router as alerts_router
from app.api.auth import get_current_user, get_db
from app.api.dashboard import router as dashboard_router
from app.api.equipment import get_db as get_equipment_db
from app.api.equipment import router as equipment_router
from app.models.alert import Alert
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor_reading import SensorReading
from tests.test_history import START, history_client


@pytest.fixture
def dashboard_client(history_client):
    app, client, _ = history_client
    app.include_router(dashboard_router)
    app.include_router(alerts_router)
    app.include_router(equipment_router)
    db = app.dependency_overrides[get_db]()
    app.dependency_overrides[get_equipment_db] = lambda: db
    now = datetime.now(timezone.utc)
    db.add(Equipment(id=4, user_id=1, identifier="AC4", name="Unused", equipment_type="AC", location="Plant", status="inactive"))
    db.add_all([
        Inspection(id=7, equipment_id=3, user_id=1, status="active", started_at=now - timedelta(seconds=3)),
        Inspection(id=8, equipment_id=3, user_id=1, status="scheduled", scheduled_at=now + timedelta(days=2), started_at=None),
        Inspection(id=9, equipment_id=3, user_id=1, status="failed", started_at=START),
        Inspection(id=10, equipment_id=3, user_id=1, status="cancelled", started_at=START),
        Inspection(id=11, equipment_id=1, user_id=2, status="active", started_at=now),
    ])
    db.flush()
    sample = db.get(SensorReading, 1)
    db.add_all([
        SensorReading(id=identity, equipment_id=equipment, inspection_id=inspection,
                      sensor_id=sample.sensor_id, unit=sample.unit, value=value, timestamp=timestamp,
                      validation_status="valid", detection_status="anomaly", anomaly_type="above_threshold")
        for identity, equipment, inspection, value, timestamp in [
            (11, 3, 7, 45, now - timedelta(seconds=1)),
            (12, 1, 11, 98, now),
        ]
    ])
    db.flush()
    db.add_all([
        FaultClassification(source_reading_id=11, status="identified", message="Live fault",
                            matches=[{"rule_id": "DR-001", "fault_type": "overheating", "evidence_reading_ids": [11]}],
                            missing_sensor_types=[], classified_at=now),
        EquipmentHealthAssessment(equipment_id=3, inspection_id=7, trigger_reading_id=11,
                                  status="insufficient_data", message="More sensors needed", assessed_at=now,
                                  evidence_reading_ids=[11], fault_rule_ids=[], missing_sensor_types=["thermal"]),
        EquipmentHealthAssessment(equipment_id=1, inspection_id=11, trigger_reading_id=12,
                                  status="critical", message="Inconsistent owner", assessed_at=now,
                                  evidence_reading_ids=[12], fault_rule_ids=[], missing_sensor_types=[]),
    ])
    db.add_all([
        Alert(id=identity, equipment_id=equipment, inspection_id=inspection, source_reading_id=reading,
              event_type="anomaly", event_key=f"fixture-{identity}", severity=severity, status=status,
              description="Saved alert", evidence_reading_ids=[reading])
        for identity, equipment, inspection, reading, severity, status in [
            (1, 1, 1, 1, "warning", "open"),
            (2, 3, 7, 11, "critical", "open"),
            (3, 1, 1, 2, "critical", "closed"),
            (4, 2, 2, 7, "critical", "open"),
            (5, 1, 11, 12, "critical", "open"),
        ]
    ])
    db.commit()
    return app, client


def test_dashboard_counts_recent_health_attention_and_monitoring(dashboard_client):
    _, client = dashboard_client
    response = client.get("/api/dashboard")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    overview = response.json()
    assert overview["equipment"] == {"total": 3, "active": 2, "inactive": 1}
    assert overview["inspections"] == {"active": 1, "scheduled": 1, "completed": 3, "failed": 1, "cancelled": 1}
    assert overview["health"] == {"normal": 0, "warning": 1, "critical": 0, "insufficient_data": 1, "not_evaluated": 1}
    assert overview["alerts"] == {"total": 2, "warning": 1, "critical": 1}
    activity = overview["recent_inspections"]
    assert activity[0]["id"] == 7
    assert {item["equipment_id"] for item in activity} == {1, 3}
    assert {item["id"] for item in activity} == {1, 3, 5, 7, 8, 9, 10}
    attention = {item["equipment_id"]: item for item in overview["attention"]}
    assert set(attention) == {1, 3}
    assert attention[1]["reasons"] == ["Open alerts"]
    assert attention[3]["reasons"] == ["Open alerts", "Recent live anomaly", "Recent live fault"]
    live, historical = overview["monitoring"]
    assert (live["equipment_id"], live["inspection_id"], live["is_live"]) == (3, 7, True)
    assert live["health_status"] == "insufficient_data"
    current = next(item for item in live["sensors"] if item["sensor_type"] == "temperature")
    assert current["status"] == "current" and current["value"] == 45 and current["timestamp"] and current["unit"]
    assert (historical["equipment_id"], historical["inspection_id"], historical["is_live"]) == (1, 5, False)
    assert historical["alert_summary"] == {"warning": 1, "critical": 0}
    assert all(item["status"] == "missing" for item in historical["sensors"])


def test_dashboard_empty_and_unauthenticated(dashboard_client):
    app, client = dashboard_client
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=99)
    response = client.get("/api/dashboard")
    assert response.status_code == 200, response.text
    overview = response.json()
    assert overview["equipment"]["total"] == overview["alerts"]["total"] == 0
    assert set(overview["health"].values()) == set(overview["inspections"].values()) == {0}
    assert overview["recent_inspections"] == overview["attention"] == overview["monitoring"] == []
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/api/dashboard").status_code == 401


def test_closing_alert_keeps_history_and_updates_dashboard(dashboard_client):
    _, client = dashboard_client
    assert client.post("/api/equipment/2/alerts/4/close").status_code == 404
    assert client.post("/api/equipment/1/alerts/5/close").status_code == 404
    path = "/api/equipment/1/alerts/1/close"
    assert client.post(path).status_code == 204
    assert client.post(path).status_code == 204
    assert client.get("/api/equipment/1/alerts?status=open").json()["items"] == []
    assert {alert["id"] for alert in client.get("/api/equipment/1/alerts?status=closed").json()["items"]} == {1, 3}
    overview = client.get("/api/dashboard").json()
    assert overview["alerts"] == {"total": 1, "warning": 0, "critical": 1}
    assert [item["equipment_id"] for item in overview["attention"]] == [3]


def test_equipment_status_update_is_validated_and_owned(dashboard_client):
    _, client = dashboard_client
    assert client.put("/api/equipment/2", json={"status": "inactive"}).status_code == 404
    assert client.put("/api/equipment/1", json={"status": "other"}).status_code == 422
    assert client.put("/api/equipment/1", json={"status": None}).status_code == 422
    response = client.put("/api/equipment/1", json={"status": "inactive"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "inactive"
    assert client.get("/api/dashboard").json()["equipment"]["inactive"] == 2
    assert client.put("/api/equipment/1", json={"status": "active"}).json()["status"] == "active"
