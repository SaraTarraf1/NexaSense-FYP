from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_current_user, get_db
from app.api.equipment_monitoring import router as monitoring_router
from app.api.inspections import router as inspections_router
from app.api.sensor_readings import router as readings_router
from app.core.database import Base
from app.models.equipment import Equipment
from app.models.sensor import Sensor
from app.models.user import User
from app.services.inspection_service import record_due_inspection_reminders
from app.services.sensor_collection_service import collect_inspection_readings
from app.services.sensor_configuration import SENSOR_DEFINITIONS


@pytest.fixture
def inspection_api(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        Base.metadata.create_all(connection)
    app = FastAPI()
    app.include_router(inspections_router)
    app.include_router(monitoring_router)
    app.include_router(readings_router)

    class Clock:
        current = datetime.now(timezone.utc).replace(microsecond=0)

        @classmethod
        def now(cls, tz):
            return cls.current.astimezone(tz)

    monkeypatch.setattr("app.services.inspection_service.datetime", Clock)
    try:
        with Session(engine, autoflush=False) as db, TestClient(app) as client:
            owner = User(full_name="Test owner", email="owner@example.com", password_hash="unused")
            db.add(owner)
            db.flush()
            equipment = Equipment(
                user_id=owner.id, identifier="AC1", name="Test AC",
                equipment_type="Air conditioner", location="Lab",
            )
            db.add(equipment)
            db.add_all([
                Sensor(sensor_type=kind, **definition)
                for kind, definition in SENSOR_DEFINITIONS.items()
            ])
            db.flush()
            owner_id = owner.id
            db.commit()
            app.dependency_overrides[get_db] = lambda: db
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=owner_id)
            yield app, client, db, equipment, Clock
    finally:
        engine.dispose()


def test_scheduling_requires_a_future_time_and_rejects_the_same_slot(inspection_api):
    app, client, _, equipment, clock = inspection_api
    scheduled_at = clock.current + timedelta(minutes=20)
    data = {
        "equipment_id": equipment.id,
        "scheduled_at": scheduled_at.isoformat(),
        "notes": "  Check airflow.  ",
    }
    response = client.post("/api/inspections/schedule", json=data)
    assert response.status_code == 201, response.text
    scheduled = response.json()
    assert scheduled["status"] == "scheduled"
    assert scheduled["created_at"]
    assert scheduled["started_at"] is None
    assert scheduled["ended_at"] is None
    assert scheduled["notes"] == "Check airflow."
    assert client.get("/api/inspections").json()[0]["id"] == scheduled["id"]

    offset = timezone(timedelta(hours=2))
    same_time = scheduled_at.astimezone(offset).isoformat()
    assert client.post("/api/inspections/schedule", json={**data, "scheduled_at": same_time}).status_code == 409
    assert client.post("/api/inspections/schedule", json={
        **data, "scheduled_at": clock.current.isoformat()
    }).status_code == 422
    assert client.post("/api/inspections/schedule", json={
        **data, "scheduled_at": scheduled_at.replace(tzinfo=None).isoformat()
    }).status_code == 422

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=999)
    assert client.post("/api/inspections/schedule", json=data).status_code == 404
    assert client.post(f"/api/inspections/{scheduled['id']}/start").status_code == 404


def test_scheduled_execution_respects_active_inspections_and_keeps_failed_results(inspection_api):
    _, client, db, equipment, clock = inspection_api
    equipment_id = equipment.id
    scheduled_at = clock.current + timedelta(minutes=1)
    scheduled = client.post("/api/inspections/schedule", json={
        "equipment_id": equipment_id, "scheduled_at": scheduled_at.isoformat()
    }).json()
    scheduled_id = scheduled["id"]
    start_url = f"/api/inspections/{scheduled_id}/start"
    assert client.post(start_url).status_code == 409
    assert collect_inspection_readings(db, scheduled_id) == []

    manual = client.post("/api/inspections", json={"equipment_id": equipment_id})
    assert manual.status_code == 201
    manual_id = manual.json()["id"]
    assert manual.json()["scheduled_at"] is None
    monitoring = client.get(f"/api/equipment/{equipment_id}/monitoring").json()
    assert monitoring["inspection_id"] == manual_id
    assert monitoring["is_live"] is True

    clock.current = scheduled_at
    assert client.post(start_url).status_code == 409
    assert client.post(f"/api/inspections/{manual_id}/complete").status_code == 200

    thermal = db.scalars(select(Sensor).where(Sensor.sensor_type == "thermal")).one()
    thermal.is_active = False
    db.commit()
    assert client.post(start_url).status_code == 409
    thermal.is_active = True
    db.commit()

    started = client.post(start_url)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "active"
    assert started.json()["started_at"] is not None
    assert client.post(start_url).status_code == 409
    assert len(collect_inspection_readings(db, scheduled_id)) == 3
    db.commit()

    failed = client.post(f"/api/inspections/{scheduled_id}/fail", json={
        "failure_reason": "  Sensor disconnected.  "
    })
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["failure_reason"] == "Sensor disconnected."
    assert failed.json()["ended_at"] is not None
    assert collect_inspection_readings(db, scheduled_id) == []
    assert len(client.get(f"/api/inspections/{scheduled_id}/readings").json()) == 3


def test_ready_reminder_is_owner_only_and_recorded_once_after_blockers_clear(inspection_api):
    app, client, db, equipment, clock = inspection_api
    equipment_id = equipment.id
    due = clock.current + timedelta(minutes=1)
    scheduled = client.post("/api/inspections/schedule", json={
        "equipment_id": equipment_id, "scheduled_at": due.isoformat()
    }).json()
    inspection_id = scheduled["id"]

    def run_reminders():
        record_due_inspection_reminders(db)
        db.commit()

    run_reminders()
    assert client.get("/api/inspections/reminders").json() == []

    active = client.post("/api/inspections", json={"equipment_id": equipment_id}).json()
    clock.current = due
    run_reminders()
    details = client.get(f"/api/inspections/{inspection_id}").json()
    assert "Another inspection is running" in details["start_blocker"]
    assert client.get("/api/inspections/reminders").json() == []
    assert client.post(f"/api/inspections/{active['id']}/complete").status_code == 200

    run_reminders()
    response = client.get("/api/inspections/reminders")
    assert response.status_code == 200, response.text
    reminder, = response.json()
    assert reminder["inspection_id"] == inspection_id
    assert reminder["equipment_name"] == "Test AC"
    assert client.get(f"/api/inspections/{inspection_id}").json()["status"] == "scheduled"
    clock.current += timedelta(minutes=10)
    run_reminders()
    assert client.get("/api/inspections/reminders").json() == [reminder]

    original_user = app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=999)
    assert client.get("/api/inspections/reminders").json() == []
    app.dependency_overrides[get_current_user] = original_user

    assert client.post(f"/api/inspections/{inspection_id}/start").status_code == 200
    assert client.get("/api/inspections/reminders").json() == []


def test_cancelling_booking_is_owner_only_and_frees_slot(inspection_api):
    app, client, db, equipment, clock = inspection_api
    due = clock.current + timedelta(minutes=1)
    payload = {"equipment_id": equipment.id, "scheduled_at": due.isoformat()}
    scheduled = client.post("/api/inspections/schedule", json=payload).json()
    inspection_id = scheduled["id"]
    url = f"/api/inspections/{inspection_id}"
    original_user = app.dependency_overrides[get_current_user]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=999)
    assert client.post(f"{url}/cancel-booking").status_code == 404
    app.dependency_overrides[get_current_user] = original_user

    cancelled = client.post(f"{url}/cancel-booking")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["started_at"] is None
    assert cancelled.json()["ended_at"] is not None
    assert client.post(f"{url}/start").status_code == 409
    assert client.post(f"{url}/cancel-booking").status_code == 409

    replacement = client.post("/api/inspections/schedule", json=payload)
    assert replacement.status_code == 201, replacement.text
    clock.current = due
    record_due_inspection_reminders(db)
    db.commit()
    reminder, = client.get("/api/inspections/reminders").json()
    assert reminder["inspection_id"] == replacement.json()["id"]

    replacement_url = f"/api/inspections/{replacement.json()['id']}"
    assert client.post(f"{replacement_url}/start").status_code == 200
    assert client.post(f"{replacement_url}/cancel-booking").status_code == 409
    assert client.get(replacement_url).json()["status"] == "active"
