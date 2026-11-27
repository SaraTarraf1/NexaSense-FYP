from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_current_user, get_db
from app.api.equipment_monitoring import router
from app.api.sensor_readings import router as readings_router
from app.core.database import Base
from app.models.alert import Alert
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.services.sensor_configuration import SENSOR_DEFINITIONS
from app.services.sensor_reading_service import save_sensor_reading


@contextmanager
def monitoring_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(router)
    app.include_router(readings_router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    with Session(engine) as db, TestClient(app) as client:
        app.dependency_overrides[get_db] = lambda: db
        yield db, client

    engine.dispose()


def test_monitoring_returns_recent_anomalies_for_the_active_inspection():
    with monitoring_client() as (db, client):
        equipment = Equipment(
            user_id=1,
            identifier="AC1",
            name="Server Room AC",
            equipment_type="Air conditioner",
            location="Server Room",
        )
        sensor = Sensor(sensor_type="temperature", **SENSOR_DEFINITIONS["temperature"])
        db.add_all([equipment, sensor])
        db.flush()

        old = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(old)
        db.flush()
        save_sensor_reading(db, old.id, "temperature", 100.0)
        old.status = "completed"

        active = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(active)
        db.flush()
        older_anomaly = save_sensor_reading(db, active.id, "temperature", 90.0)
        newer_anomaly = save_sensor_reading(db, active.id, "temperature", 15.0)
        save_sensor_reading(db, active.id, "temperature", 35.0)
        save_sensor_reading(db, active.id, "temperature", 999.0)
        save_sensor_reading(db, active.id, "temperature", None)

        endpoint = f"/api/equipment/{equipment.id}/monitoring"
        response = client.get(endpoint)
        assert response.status_code == 200
        monitoring = response.json()
        assert monitoring["inspection_id"] == active.id
        assert [item["reading_id"] for item in monitoring["anomalies"]] == [
            newer_anomaly.id,
            older_anomaly.id,
        ]
        assert monitoring["anomalies"][0] == {
            "reading_id": newer_anomaly.id,
            "sensor_type": "temperature",
            "value": 15.0,
            "unit": sensor.unit,
            "timestamp": newer_anomaly.timestamp.isoformat(),
            "anomaly_type": "below_threshold",
            "message": newer_anomaly.detection_message,
        }

        active.status = "completed"
        db.flush()
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json()["anomalies"] == []


def test_monitoring_surfaces_fault_evidence_for_the_latest_inspection():
    with monitoring_client() as (db, client):
        equipment = Equipment(
            user_id=1,
            identifier="AC1",
            name="Server Room AC",
            equipment_type="Air conditioner",
            location="Server Room",
        )
        db.add(equipment)
        db.add_all([
            Sensor(sensor_type="temperature", **SENSOR_DEFINITIONS["temperature"]),
            Sensor(sensor_type="thermal", **SENSOR_DEFINITIONS["thermal"]),
        ])
        db.flush()

        previous = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(previous)
        db.flush()
        previous_reading = save_sensor_reading(db, previous.id, "temperature", 100.0)
        db.add(FaultClassification(
            source_reading_id=previous_reading.id,
            status="unknown",
            message="No diagnostic rule matched.",
            matches=[],
            missing_sensor_types=[],
        ))
        previous.status = "completed"

        latest = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(latest)
        db.flush()
        temperature = save_sensor_reading(db, latest.id, "temperature", 90.0)
        thermal = save_sensor_reading(db, latest.id, "thermal", 145.0)
        later_anomaly = save_sensor_reading(db, latest.id, "temperature", 80.0)
        db.add_all([
            FaultClassification(
                source_reading_id=temperature.id,
                status="identified",
                message="Sensor readings match a rule.",
                matches=[{
                    "rule_id": "DR-001",
                    "fault_type": "overheating",
                    "evidence_reading_ids": [temperature.id, thermal.id],
                }],
                missing_sensor_types=[],
            ),
            FaultClassification(
                source_reading_id=later_anomaly.id,
                status="undetermined",
                message="Recent supporting readings are missing.",
                matches=[],
                missing_sensor_types=["thermal"],
            ),
        ])
        db.flush()

        endpoint = f"/api/equipment/{equipment.id}/monitoring"
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json()["is_live"] is True
        faults = response.json()["faults"]
        assert [fault["status"] for fault in faults] == ["undetermined", "identified"]
        assert faults[0]["source_reading"]["reading_id"] == later_anomaly.id
        assert faults[0]["missing_sensor_types"] == ["thermal"]
        match = faults[1]["matches"][0]
        assert match["rule_id"] == "DR-001"
        assert match["fault_type"] == "overheating"
        assert match["evidence_reading_ids"] == [temperature.id, thermal.id]
        assert [
            (item["sensor_type"], item["value"], item["unit"])
            for item in match["evidence"]
        ] == [("temperature", 90.0, temperature.unit), ("thermal", 145.0, thermal.unit)]

        latest.status = "completed"
        db.flush()
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json()["is_live"] is False
        assert response.json()["faults"] == faults

        new_inspection = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(new_inspection)
        db.flush()
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json()["inspection_id"] == new_inspection.id
        assert response.json()["faults"] == []


def test_monitoring_keeps_recent_health_attempts_and_the_last_completed_result():
    with monitoring_client() as (db, client):
        equipment = Equipment(
            user_id=1, identifier="AC1", name="Server Room AC",
            equipment_type="Air conditioner", location="Server Room",
        )
        db.add(equipment)
        db.add(Sensor(sensor_type="temperature", **SENSOR_DEFINITIONS["temperature"]))
        db.flush()
        previous = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(previous)
        db.flush()
        previous_reading = save_sensor_reading(db, previous.id, "temperature", 35.0)
        previous.status = "completed"
        assessed_at = datetime(2026, 11, 26, 10, tzinfo=timezone.utc)
        completed = EquipmentHealthAssessment(
            equipment_id=equipment.id,
            inspection_id=previous.id,
            trigger_reading_id=previous_reading.id,
            status="normal",
            message="All readings were within range.",
            assessed_at=assessed_at,
            evidence_reading_ids=[previous_reading.id],
            fault_rule_ids=[],
            missing_sensor_types=[],
        )
        db.add(completed)
        db.flush()

        endpoint = f"/api/equipment/{equipment.id}/monitoring"
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json()["health_status"] == "normal"
        assert response.json()["health_assessment"]["evidence"][0]["reading_id"] == previous_reading.id

        current = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(current)
        db.flush()
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json()["health_status"] == "not_evaluated"
        assert response.json()["health_assessment"] is None
        assert response.json()["last_completed_health_assessment"]["id"] == completed.id

        for offset in range(1, 22):
            reading = save_sensor_reading(db, current.id, "temperature", 40.0)
            attempt = EquipmentHealthAssessment(
                equipment_id=equipment.id,
                inspection_id=current.id,
                trigger_reading_id=reading.id,
                status="insufficient_data",
                message="Required observations are missing.",
                assessed_at=assessed_at + timedelta(seconds=offset),
                evidence_reading_ids=[reading.id, previous_reading.id],
                fault_rule_ids=[],
                missing_sensor_types=["vibration", "thermal"],
            )
            db.add(attempt)
        db.flush()

        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["health_status"] == "insufficient_data"
        assert data["health_assessment"]["id"] == attempt.id
        assert data["health_assessment"]["missing_sensor_types"] == ["vibration", "thermal"]
        assert [item["reading_id"] for item in data["health_assessment"]["evidence"]] == [reading.id]
        assert data["last_completed_health_assessment"]["id"] == completed.id
        assert len(data["health_history"]) == 20
        assert data["health_history"][0]["id"] == attempt.id
        assert all(entry["inspection_id"] == current.id for entry in data["health_history"])


def test_monitoring_poll_updates_valid_readings_and_open_alerts_for_owned_equipment():
    with monitoring_client() as (db, client):
        equipment = Equipment(
            user_id=1, identifier="AC1", name="Owned AC",
            equipment_type="Air conditioner", location="Lab",
        )
        other_equipment = Equipment(
            user_id=2, identifier="AC2", name="Other AC",
            equipment_type="Air conditioner", location="Lab",
        )
        sensor = Sensor(sensor_type="temperature", **SENSOR_DEFINITIONS["temperature"])
        db.add_all([equipment, other_equipment, sensor])
        db.flush()
        inspection = Inspection(equipment_id=equipment.id, user_id=1)
        other_inspection = Inspection(equipment_id=other_equipment.id, user_id=2)
        db.add_all([inspection, other_inspection])
        db.flush()

        endpoint = f"/api/equipment/{equipment.id}/monitoring"
        initial = client.get(endpoint)
        assert initial.headers["cache-control"] == "no-store"
        assert initial.json()["alert_summary"] == {"warning": 0, "critical": 0}

        reading = save_sensor_reading(db, inspection.id, "temperature", 35.0)
        save_sensor_reading(db, inspection.id, "temperature", 999.0)
        other_reading = save_sensor_reading(db, other_inspection.id, "temperature", 39.0)
        for value, severity, status, key in (
            (reading, "warning", "open", "owned_open"),
            (reading, "critical", "closed", "owned_closed"),
            (other_reading, "critical", "open", "other_open"),
        ):
            db.add(Alert(
                equipment_id=value.equipment_id, inspection_id=value.inspection_id,
                source_reading_id=value.id, event_type="anomaly", event_key=key,
                severity=severity, status=status, description="Test alert",
                evidence_reading_ids=[value.id],
            ))
        db.commit()

        updated = client.get(endpoint).json()
        assert updated["equipment_id"] == equipment.id
        assert updated["observed_at"] >= initial.json()["observed_at"]
        assert updated["alert_summary"] == {"warning": 1, "critical": 0}
        assert next(sensor for sensor in updated["sensors"] if sensor["sensor_type"] == "temperature")["value"] == 35.0
        assert client.get(f"/api/equipment/{other_equipment.id}/monitoring").status_code == 404

        latest_url = f"/api/inspections/{inspection.id}/readings/latest"
        latest = client.get(
            latest_url, params={"validated_only": True}, headers={"Origin": "http://localhost:5173"}
        )
        assert latest.headers["cache-control"] == "no-store"
        assert latest.headers["access-control-expose-headers"] == "X-Observed-At"
        assert datetime.fromisoformat(latest.headers["x-observed-at"]).utcoffset() == timedelta(0)
        validated, = latest.json()
        assert validated["id"] == reading.id
        assert validated["freshness_threshold_seconds"] == sensor.collection_interval_seconds * 3
        unfiltered, = client.get(latest_url).json()
        assert unfiltered["validation_status"] == "invalid"
        assert client.get(f"/api/inspections/{other_inspection.id}/readings/latest").status_code == 404

def test_monitoring_excludes_future_readings():
    with monitoring_client() as (db, client):
        equipment = Equipment(
            user_id=1,
            identifier="AC1",
            name="Test AC",
            equipment_type="Air conditioner",
            location="Lab",
        )

        sensor = Sensor(
            sensor_type="temperature",
            **SENSOR_DEFINITIONS["temperature"],
        )

        db.add_all([equipment, sensor])
        db.flush()

        inspection = Inspection(
            equipment_id=equipment.id,
            user_id=1,
        )

        db.add(inspection)
        db.flush()

        valid = save_sensor_reading(
            db, inspection.id, "temperature", 35.0
        )

        future = save_sensor_reading(
            db, inspection.id, "temperature", 100.0
        )

        future.timestamp = (
            datetime.now(timezone.utc)
            + timedelta(minutes=10)
        )

        db.commit()

        response = client.get(
            f"/api/equipment/{equipment.id}/monitoring"
        )

        assert response.status_code == 200

        data = response.json()

        temperature = next(
            item for item in data["sensors"]
            if item["sensor_type"] == "temperature"
        )

        assert temperature["value"] == 35.0
        assert temperature["status"] == "current"
        assert data["anomalies"] == []

        response = client.get(
            f"/api/inspections/{inspection.id}/readings/latest",
            params={"validated_only": True},
        )

        assert response.status_code == 200
        assert response.json()[0]["id"] == valid.id

def test_monitoring_does_not_mix_completed_inspections():
    with monitoring_client() as (db, client):
        equipment = Equipment(
            user_id=1,
            identifier="AC1",
            name="Test AC",
            equipment_type="Air conditioner",
            location="Lab",
        )

        db.add(equipment)

        db.add_all([
            Sensor(
                sensor_type="temperature",
                **SENSOR_DEFINITIONS["temperature"],
            ),
            Sensor(
                sensor_type="thermal",
                **SENSOR_DEFINITIONS["thermal"],
            ),
        ])

        db.flush()

        previous = Inspection(
            equipment_id=equipment.id,
            user_id=1,
        )

        db.add(previous)
        db.flush()

        save_sensor_reading(
            db, previous.id, "temperature", 35.0
        )

        save_sensor_reading(
            db, previous.id, "thermal", 45.0
        )

        previous.status = "completed"
        db.flush()

        latest = Inspection(
            equipment_id=equipment.id,
            user_id=1,
        )

        db.add(latest)
        db.flush()

        save_sensor_reading(
            db, latest.id, "temperature", 40.0
        )

        latest.status = "completed"
        db.commit()

        response = client.get(
            f"/api/equipment/{equipment.id}/monitoring"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["inspection_id"] == latest.id
        assert data["is_live"] is False

        sensors = {
            item["sensor_type"]: item
            for item in data["sensors"]
        }

        assert sensors["temperature"]["value"] == 40.0
        assert sensors["thermal"]["value"] is None
        assert sensors["thermal"]["status"] == "missing"

def test_monitoring_marks_old_readings_as_stale():
    with monitoring_client() as (db, client):
        equipment = Equipment(
            user_id=1,
            identifier="AC1",
            name="Test AC",
            equipment_type="Air conditioner",
            location="Lab",
        )

        sensor = Sensor(
            sensor_type="temperature",
            **SENSOR_DEFINITIONS["temperature"],
        )

        db.add_all([equipment, sensor])
        db.flush()

        inspection = Inspection(
            equipment_id=equipment.id,
            user_id=1,
        )

        db.add(inspection)
        db.flush()

        reading = save_sensor_reading(
            db, inspection.id, "temperature", 35.0
        )

        reading.timestamp = (
            datetime.now(timezone.utc)
            - timedelta(minutes=5)
        )

        db.commit()

        response = client.get(
            f"/api/equipment/{equipment.id}/monitoring"
        )

        assert response.status_code == 200

        data = response.json()

        temperature = next(
            item for item in data["sensors"]
            if item["sensor_type"] == "temperature"
        )

        assert data["is_live"] is True
        assert temperature["status"] == "stale"
        assert temperature["value"] == 35.0