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
