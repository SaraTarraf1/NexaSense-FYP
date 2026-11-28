from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_current_user, get_db
from app.api.history import router
from app.core.database import Base
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.services.sensor_configuration import SENSOR_DEFINITIONS


START = datetime(2026, 11, 1, tzinfo=timezone.utc)
END = START + timedelta(days=1)
PERIOD = {"start": "2026-11-01T02:00:00+02:00", "end": END.isoformat()}


@pytest.fixture
def history_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    with Session(engine) as db, TestClient(app) as client:
        app.dependency_overrides[get_db] = lambda: db
        db.add_all([
            Equipment(id=id_, user_id=owner, identifier=f"AC{id_}", name=f"Unit {id_}",
                      equipment_type="AC", location="Plant")
            for id_, owner in [(1, 1), (2, 2), (3, 1)]
        ])
        sensor = Sensor(sensor_type="temperature", **SENSOR_DEFINITIONS["temperature"])
        db.add(sensor)
        db.flush()
        db.add_all([
            Inspection(id=id_, equipment_id=equipment, user_id=owner, status="completed", started_at=START)
            for id_, equipment, owner in [(1, 1, 1), (2, 2, 2), (3, 3, 1), (4, 1, 2), (5, 1, 1)]
        ])
        for id_, inspection, equipment, timestamp, value, status in [
            (1, 1, 1, START, 20, "valid"),
            (2, 1, 1, START, 40, "valid"),
            (3, 1, 1, START + timedelta(hours=1), 90, "invalid"),
            (4, 1, 1, START + timedelta(hours=2), None, "missing"),
            (5, 1, 1, START + timedelta(hours=3), float("inf"), "valid"),
            (6, 1, 1, END, 100, "valid"),
            (7, 2, 2, START, 100, "valid"),
            (8, 3, 3, START, 100, "valid"),
            (9, 4, 1, START, 100, "valid"),
            (10, 1, 1, START - timedelta(seconds=1), 100, "valid"),
        ]:
            db.add(SensorReading(
                id=id_, sensor_id=sensor.id, equipment_id=equipment, inspection_id=inspection,
                timestamp=timestamp, value=value, unit=sensor.unit, validation_status=status,
                validation_message="Rejected" if status != "valid" else None,
                detection_status="anomaly" if id_ in {1, 2, 7, 9} else "not_evaluated",
                anomaly_type="above_threshold" if id_ in {1, 2, 7, 9} else None,
            ))
        db.flush()
        db.add_all([
            FaultClassification(source_reading_id=identity, status="identified", message="Saved fault",
                                matches=[{"rule_id": "fixture", "fault_type": "overheating", "evidence_reading_ids": [1, 7]}],
                                missing_sensor_types=[], classified_at=START)
            for identity in [1, 2, 7]
        ])
        db.add_all([
            EquipmentHealthAssessment(equipment_id=1, inspection_id=1, trigger_reading_id=identity,
                                      status=status, message="Saved assessment", assessed_at=START + timedelta(minutes=identity),
                                      evidence_reading_ids=[identity], fault_rule_ids=[], missing_sensor_types=[])
            for identity, status in [(1, "insufficient_data"), (2, "warning")]
        ])
        db.commit()
        yield app, client, engine
    engine.dispose()


def test_summary_is_scoped_and_read_only(history_client):
    _, client, engine = history_client
    statements = []

    def capture(_conn, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    response = client.get("/api/equipment/1/history", params=PERIOD)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["inspections"] == 2
    assert data["valid_measurements"] == 2
    assert data["anomalies"] == data["faults"] == data["health_assessments"] == 2
    assert data["anomaly_types"] == [{"type": "above_threshold", "count": 2, "frequency": 1}]
    assert data["fault_types"] == [{"type": "overheating", "count": 2, "frequency": 1}]
    group, = data["sensors"]
    assert (group["minimum"], group["maximum"], group["average"], group["count"]) == (20, 40, 30, 2)
    assert [point["value"] for point in group["points"]] == [20, 40]
    assert statements and all(statement.lstrip().startswith("SELECT") for statement in statements)


def test_records_are_paginated_ordered_and_preserve_stored_analysis(history_client):
    _, client, _ = history_client

    def records(section, **params):
        result = client.get(f"/api/equipment/1/history/{section}", params=PERIOD | params)
        assert result.status_code == 200, result.text
        return result.json()

    page = records("readings", limit=2, offset=2)
    assert page["total"] == 5
    assert [item["id"] for item in page["items"]] == [3, 4]
    assert [item["validation_status"] for item in page["items"]] == ["invalid", "missing"]
    assert page["items"][0]["validation_message"] == "Rejected"
    assert records("readings", offset=4)["items"][0]["value"] is None
    assert [item["id"] for item in records("anomalies")["items"]] == [1, 2]
    fault = records("faults")["items"][0]
    assert [item["id"] for item in fault["matches"][0]["evidence"]] == [1]
    assert [item["status"] for item in records("health")["items"]] == ["insufficient_data", "warning"]
    assert [item["health_status"] for item in records("inspections")["items"]] == ["warning", "not_evaluated"]


def test_history_authorization_ranges_and_empty_period(history_client):
    app, client, _ = history_client
    assert client.get("/api/equipment/2/history", params=PERIOD).status_code == 404
    assert client.get("/api/equipment/2/history/readings", params=PERIOD).status_code == 404
    assert client.get("/api/equipment/1/history", params=PERIOD | {"end": PERIOD["start"]}).status_code == 422
    assert client.get("/api/equipment/1/history", params=PERIOD | {"start": "2026-11-01T00:00:00"}).status_code == 422
    empty = {"start": END.isoformat(), "end": (END + timedelta(days=1)).isoformat()}
    result = client.get("/api/equipment/3/history", params=empty)
    assert result.status_code == 200
    assert result.json()["sensors"] == []
    assert result.json()["inspections"] == 0
    assert client.get("/api/equipment/3/history/readings", params=empty).json()["items"] == []
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/api/equipment/1/history", params=PERIOD).status_code == 401
