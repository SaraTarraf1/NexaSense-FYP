from datetime import timedelta
import re
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.api.auth import get_current_user, get_db
from app.api.reports import router
from app.models.alert import Alert
from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.inspection_report import InspectionReport
from app.models.sensor_reading import SensorReading
from app.services.fault_configuration import FAULT_RULES
from app.services.report_service import FAULT_ACTIONS, maintenance_actions
from tests.test_history import START, history_client


@pytest.fixture
def report_client(history_client):
    app, client, _ = history_client
    app.include_router(router)
    db = app.dependency_overrides[get_db]()
    db.get(Inspection, 1).ended_at = START + timedelta(minutes=5)
    db.add_all([
        Alert(equipment_id=1, inspection_id=1, source_reading_id=1, event_type="anomaly", event_key="owned",
              severity="warning", description="Saved warning", status="closed", evidence_reading_ids=[1]),
        Alert(equipment_id=2, inspection_id=2, source_reading_id=7, event_type="anomaly", event_key="other",
              severity="critical", description="Other equipment's alert", status="open", evidence_reading_ids=[7]),
    ])
    db.commit()
    return app, client, db


def generate(client, equipment=1, inspection=1):
    return client.post("/api/reports", json={"equipment_id": equipment, "inspection_id": inspection})


def test_report_owned_persisted_and_idempotent(report_client):
    _, client, db = report_client
    eligible = client.get("/api/reports/eligible/1").json()
    assert {item["id"] for item in eligible["items"]} == {1, 5}
    baseline = db.get(SensorReading, 1).value
    result = generate(client)
    assert result.status_code == 200, result.text
    report = result.json()
    snapshot = report["snapshot"]
    assert [reading["id"] for reading in snapshot["readings"]] == [10, 1, 2, 3, 4, 5, 6]
    assert snapshot["duration_seconds"] == 300
    assert snapshot["health_status"] == "warning"
    assert snapshot["statistics"][0]["count"] == 4
    assert [reading["id"] for reading in snapshot["anomalies"]] == [1, 2]
    assert snapshot["faults"][0]["matches"][0]["evidence"][0]["id"] == 1
    assert [(alert["severity"], alert["description"], alert["status"]) for alert in snapshot["alerts"]] == [
        ("warning", "Saved warning", "closed")
    ]
    assert snapshot["recommendations"] == [FAULT_ACTIONS["overheating"], "Schedule a maintenance review."]
    assert db.get(SensorReading, 1).value == baseline
    assert db.get(Inspection, 1).status == "completed"
    assert db.scalar(select(func.count(InspectionReport.id))) == 1

    db.get(SensorReading, 1).value = 77
    db.get(Equipment, 1).name = "Later registry name"
    db.commit()
    assert generate(client).json() == report
    assert client.get(f"/api/reports/{report['id']}").json() == report
    assert client.get("/api/reports?equipment_id=1").json()["items"][0]["equipment_name"] == "Unit 1"
    assert db.scalar(select(func.count(InspectionReport.id))) == 1
    assert db.get(SensorReading, 1).value == 77


def test_report_authorization_and_eligibility(report_client):
    app, client, db = report_client
    db.add_all([
        Inspection(id=6, equipment_id=1, user_id=1, status="active", started_at=START),
        Inspection(id=7, equipment_id=1, user_id=1, status="scheduled", scheduled_at=START, started_at=None),
        Inspection(id=8, equipment_id=1, user_id=1, status="cancelled", started_at=START),
        Inspection(id=9, equipment_id=1, user_id=1, status="failed", started_at=START),
    ])
    db.commit()
    for inspection in [6, 7, 8, 9]:
        assert generate(client, inspection=inspection).status_code == 409
    assert generate(client, equipment=2, inspection=2).status_code == 404
    assert generate(client, equipment=1, inspection=3).status_code == 404
    assert generate(client, equipment=1, inspection=4).status_code == 404
    report = generate(client).json()
    path = f"/api/reports/{report['id']}"
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2)
    assert client.get(path).status_code == 404
    assert client.get(f"{path}/pdf").status_code == 404
    assert client.get("/api/reports").json()["total"] == 0
    assert client.get("/api/reports?equipment_id=1").status_code == 404
    assert client.get("/api/reports/eligible/1").status_code == 404
    app.dependency_overrides.pop(get_current_user)
    assert generate(client).status_code == 401
    assert client.get(path).status_code == 401


def test_missing_report_data_and_pdf_pagination(report_client):
    _, client, db = report_client
    empty = generate(client, inspection=5).json()["snapshot"]
    assert empty["readings"] == []
    assert empty["statistics"] == []
    assert empty["health_status"] == "not_evaluated"
    assert len(empty["limitations"]) == 3
    assert empty["recommendations"]

    reading = db.get(SensorReading, 1)
    db.add_all(
        SensorReading(
            sensor_id=reading.sensor_id, equipment_id=1, inspection_id=1,
            value=reading.value, unit=reading.unit, timestamp=START + timedelta(seconds=index),
            validation_status="valid",
        )
        for index in range(240)
    )
    db.commit()
    report = generate(client).json()
    response = client.get(f"/api/reports/{report['id']}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == f'attachment; filename="nexasense-report-{report["id"]}.pdf"'
    assert response.content.startswith(b"%PDF-")
    assert len(re.findall(rb"/Type\s*/Page\b", response.content)) > 2


def test_recommendations_cover_saved_rule_types_and_indeterminate_outcomes():
    assert set(FAULT_ACTIONS) == {rule.fault_type for rule in FAULT_RULES}
    faults = [
        {"status": "unknown", "matches": []},
        {"status": "undetermined", "matches": []},
    ]
    actions = maintenance_actions(faults, "insufficient_data")
    assert len(actions) == 3
    assert "technical inspection" in actions[0]
    assert "missing measurements" in actions[1]
    assert "required measurements" in actions[2]
    assert maintenance_actions([], "normal") == ["Continue routine preventive maintenance."]
