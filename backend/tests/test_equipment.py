from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.auth import get_current_user
from app.api.equipment import get_db
from app.core.database import Base
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.services.sensor_configuration import SENSOR_DEFINITIONS
from app.services.sensor_reading_service import save_sensor_reading


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def payload(**updates):
    return dict(name="Server Room AC", identifier="ac-001", equipment_type="Air conditioner", location="Server Room", installation_date="2023-03-01", **updates)


def test_registration_and_duplicate_identifier(client):
    response = client.post("/api/equipment", json=payload())
    assert response.status_code == 201
    equipment = response.json()
    assert equipment["identifier"] == "AC-001"
    assert equipment["user_id"] == 1
    assert equipment["status"] == "active"
    assert equipment["installation_date"] == "2023-03-01"
    assert equipment["created_at"]
    assert client.post("/api/equipment", json=payload()).status_code == 409


def test_update_and_owner_access(client):
    first = client.post("/api/equipment", json=payload()).json()
    second_payload = payload()
    second_payload["identifier"] = "AC-002"
    second = client.post("/api/equipment", json=second_payload).json()
    assert client.put(f"/api/equipment/{second['id']}", json={"identifier": "ac-001"}).status_code == 409
    response = client.put(f"/api/equipment/{first['id']}", json={"identifier": "ac-001", "location": "Office", "installation_date": None})
    assert response.status_code == 200
    assert response.json()["location"] == "Office"
    assert response.json()["installation_date"] is None
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2)
    assert client.get("/api/equipment").json() == []
    assert client.get(f"/api/equipment/{first['id']}").status_code == 404
    assert client.put(f"/api/equipment/{first['id']}", json={"name": "Other"}).status_code == 404
    assert client.post("/api/equipment", json=payload()).status_code == 201


@pytest.mark.parametrize("updates", [{"identifier": "bad id!"}, {"identifier": " "}, {"name": " "}, {"installation_date": "not-a-date"}])
def test_invalid_registration(client, updates):
    data = payload()
    data.update(updates)
    assert client.post("/api/equipment", json=data).status_code == 422


def test_required_update_fields_cannot_be_null(client):
    equipment = client.post("/api/equipment", json=payload()).json()
    for field in ("name", "equipment_type", "location", "identifier"):
        assert client.put(f"/api/equipment/{equipment['id']}", json={field: None}).status_code == 422


def test_automatic_type_identifiers(client):
    data = payload()
    del data["identifier"]
    assert client.post("/api/equipment", json=data).json()["identifier"] == "AC1"
    assert client.post("/api/equipment", json=data).json()["identifier"] == "AC2"
    data["equipment_type"] = "Water pump"
    assert client.post("/api/equipment", json=data).json()["identifier"] == "WP1"
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2)
    data["equipment_type"] = "Air conditioner"
    assert client.post("/api/equipment", json=data).json()["identifier"] == "AC1"


def test_generated_identifier_skips_custom_identifier(client):
    data = payload()
    data["identifier"] = "AC1"
    assert client.post("/api/equipment", json=data).status_code == 201
    del data["identifier"]
    assert client.post("/api/equipment", json=data).json()["identifier"] == "AC2"


def test_delete_equipment_and_owner_access(client):
    equipment = client.post("/api/equipment", json=payload()).json()
    endpoint = f"/api/equipment/{equipment['id']}"
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2)
    assert client.delete(endpoint).status_code == 404
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    assert client.get(endpoint).status_code == 200
    response = client.delete(endpoint)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(endpoint).status_code == 404
    assert client.get("/api/equipment").json() == []
    assert client.delete(endpoint).status_code == 404


def test_registry_shows_health_from_the_latest_inspection(client):
    item = client.post("/api/equipment", json=payload()).json()
    equipment_id, user_id = item["id"], item["user_id"]
    listing = client.get("/api/equipment").json()
    assert listing[0]["health_status"] == "not_evaluated"
    assert listing[0]["last_inspection_at"] is None

    db = app.dependency_overrides[get_db]()
    started_at = datetime(2026, 11, 26, 10, tzinfo=timezone.utc)
    previous = Inspection(equipment_id=equipment_id, user_id=user_id, started_at=started_at)
    db.add_all([previous, Sensor(sensor_type="temperature", **SENSOR_DEFINITIONS["temperature"])])
    db.flush()

    reading = save_sensor_reading(db, previous.id, "temperature", 35.0)
    db.add(EquipmentHealthAssessment(
        equipment_id=equipment_id, inspection_id=previous.id, trigger_reading_id=reading.id,
        status="normal", message="Current readings are within range.", assessed_at=started_at,
        evidence_reading_ids=[reading.id], fault_rule_ids=[], missing_sensor_types=[],
    ))
    previous.status = "completed"
    db.flush()

    listing = client.get("/api/equipment").json()
    assert listing[0]["health_status"] == "normal"
    assert listing[0]["last_inspection_at"].startswith("2026-11-26T10:00:00")

    current = Inspection(
        equipment_id=equipment_id, user_id=user_id, started_at=started_at + timedelta(minutes=1)
    )
    db.add(current)
    db.flush()
    listing = client.get("/api/equipment").json()
    assert listing[0]["health_status"] == "not_evaluated"
    assert listing[0]["last_inspection_at"].startswith("2026-11-26T10:01:00")

    missing = save_sensor_reading(db, current.id, "temperature", None)
    db.add(EquipmentHealthAssessment(
        equipment_id=equipment_id, inspection_id=current.id, trigger_reading_id=missing.id,
        status="insufficient_data", message="Current observations are missing.",
        assessed_at=started_at + timedelta(minutes=1), evidence_reading_ids=[],
        fault_rule_ids=[], missing_sensor_types=["temperature"],
    ))
    db.flush()
    assert client.get("/api/equipment").json()[0]["health_status"] == "insufficient_data"

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2)
    assert client.get("/api/equipment").json() == []
