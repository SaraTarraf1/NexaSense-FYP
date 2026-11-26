from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.alerts import router
from app.api.auth import get_db
from app.core import security
from app.core.database import Base
from app.models.alert import Alert
from app.models.alert_notification import AlertNotification
from app.models.equipment import Equipment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.user import User
from app.services.sensor_configuration import SENSOR_DEFINITIONS
from app.services.sensor_reading_service import save_sensor_reading


@pytest.fixture
def alerts_client(monkeypatch):
    monkeypatch.setattr(security, "SECRET_KEY", "test secret used only for equipment alert authentication")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    report_time = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
    with Session(engine) as db:
        owner = User(full_name="Equipment owner", email="owner@example.com", password_hash="unused")
        other = User(full_name="Other owner", email="other@example.com", password_hash="unused")
        db.add_all([owner, other])
        db.flush()
        equipment = Equipment(
            user_id=owner.id, identifier="AC1", name="Owner AC",
            equipment_type="Air conditioner", location="Test",
        )
        other_equipment = Equipment(
            user_id=other.id, identifier="AC1", name="Other AC",
            equipment_type="Air conditioner", location="Test",
        )
        db.add_all([equipment, other_equipment])
        db.add_all([
            Sensor(sensor_type=kind, **SENSOR_DEFINITIONS[kind])
            for kind in ("temperature", "thermal")
        ])
        db.flush()
        previous = Inspection(equipment_id=equipment.id, user_id=owner.id)
        active = Inspection(equipment_id=equipment.id, user_id=owner.id)
        other_inspection = Inspection(equipment_id=other_equipment.id, user_id=other.id)
        db.add_all([previous, active, other_inspection])
        db.flush()

        historical = save_sensor_reading(db, previous.id, "temperature", 80.0)
        previous.status = "completed"
        temperature = save_sensor_reading(db, active.id, "temperature", 90.0)
        thermal = save_sensor_reading(db, active.id, "thermal", 145.0)
        unrelated = save_sensor_reading(db, other_inspection.id, "temperature", 100.0)

        def anomaly(reading, created_at):
            return Alert(
                equipment_id=reading.equipment_id,
                inspection_id=reading.inspection_id,
                source_reading_id=reading.id,
                event_type="anomaly",
                event_key="anomaly:temperature:above_threshold",
                severity="warning",
                description="Temperature exceeds its operating range.",
                evidence_reading_ids=[reading.id],
                created_at=created_at,
            )

        earlier = anomaly(historical, report_time - timedelta(minutes=1))
        warning = anomaly(temperature, report_time)
        other_alert = anomaly(unrelated, report_time)
        fault = FaultClassification(
            source_reading_id=temperature.id,
            status="identified",
            message="DR-001 matched.",
            matches=[{
                "rule_id": "DR-001",
                "fault_type": "overheating",
                "evidence_reading_ids": [temperature.id, thermal.id],
            }],
            missing_sensor_types=[],
        )
        db.add_all([earlier, warning, other_alert, fault])
        db.flush()
        critical = Alert(
            equipment_id=equipment.id,
            inspection_id=active.id,
            source_reading_id=temperature.id,
            fault_classification_id=fault.source_reading_id,
            event_type="fault",
            event_key="fault:DR-001",
            severity="critical",
            description="Potential overheating (rule DR-001).",
            evidence_reading_ids=[thermal.id, historical.id, temperature.id, unrelated.id],
            created_at=report_time,
        )
        db.add(critical)
        db.flush()
        db.add_all([
            AlertNotification(alert_id=warning.id, recipient_user_id=owner.id),
            AlertNotification(
                alert_id=critical.id, recipient_user_id=owner.id, status="failed",
                error_message="In-app notification delivery failed.", attempted_at=report_time,
            ),
            AlertNotification(
                alert_id=critical.id, recipient_user_id=other.id, status="delivered",
                attempted_at=report_time,
            ),
        ])
        records = {
            "endpoint": f"/api/equipment/{equipment.id}/alerts",
            "owner": {"Authorization": f"Bearer {security.create_access_token(owner.id)}"},
            "other": {"Authorization": f"Bearer {security.create_access_token(other.id)}"},
            "earlier_alert": earlier.id,
            "warning_alert": warning.id,
            "critical_alert": critical.id,
            "other_alert": other_alert.id,
            "temperature_reading": temperature.id,
            "thermal_reading": thermal.id,
        }
        db.commit()

    app = FastAPI()
    app.include_router(router)

    def get_test_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(app) as client:
            yield client, records
    finally:
        engine.dispose()


def test_alert_list_is_paginated_and_preserves_failed_deliveries(alerts_client):
    client, records = alerts_client
    response = client.get(records["endpoint"], headers=records["owner"], params={"limit": 1})
    assert response.status_code == 200
    page = response.json()
    critical = page["items"][0]
    assert critical["id"] == records["critical_alert"]
    assert critical["severity"] == "critical"
    assert critical["status"] == "open"
    assert [attempt["status"] for attempt in critical["notifications"]] == ["failed"]
    assert critical["notifications"][0]["error_message"] == "In-app notification delivery failed."
    assert page["next_before_id"] == critical["id"]

    response = client.get(
        records["endpoint"], headers=records["owner"],
        params={"limit": 2, "before_id": page["next_before_id"]},
    )
    assert response.status_code == 200
    page = response.json()
    assert [alert["id"] for alert in page["items"]] == [records["warning_alert"], records["earlier_alert"]]
    assert page["items"][0]["notifications"][0]["status"] == "pending"
    assert page["items"][1]["notifications"] == []
    assert page["next_before_id"] is None


def test_alert_details_return_only_evidence_from_the_alert_inspection(alerts_client):
    client, records = alerts_client
    response = client.get(
        f"{records['endpoint']}/{records['critical_alert']}", headers=records["owner"]
    )
    assert response.status_code == 200
    details = response.json()
    assert details["source_reading_id"] == records["temperature_reading"]
    assert [
        (reading["reading_id"], reading["sensor_type"], reading["value"])
        for reading in details["evidence"]
    ] == [
        (records["thermal_reading"], "thermal", 145.0),
        (records["temperature_reading"], "temperature", 90.0),
    ]


def test_non_owners_cannot_list_or_open_alerts(alerts_client):
    client, records = alerts_client
    endpoint = records["endpoint"]
    detail = f"{endpoint}/{records['critical_alert']}"
    assert client.get(endpoint).status_code == 401
    assert client.get(detail).status_code == 401
    assert client.get(endpoint, headers=records["other"]).status_code == 404
    assert client.get(detail, headers=records["other"]).status_code == 404
    assert client.get(f"{endpoint}/{records['other_alert']}", headers=records["owner"]).status_code == 404
    assert client.get(
        endpoint, headers=records["owner"], params={"before_id": records["other_alert"]}
    ).status_code == 404
    assert client.get(endpoint, headers=records["owner"], params={"limit": 101}).status_code == 422
