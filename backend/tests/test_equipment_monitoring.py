from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_current_user, get_db
from app.api.equipment_monitoring import router
from app.core.database import Base
from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.services.sensor_configuration import SENSOR_DEFINITIONS
from app.services.sensor_reading_service import save_sensor_reading


def test_monitoring_returns_recent_anomalies_for_the_active_inspection():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    with Session(engine) as db, TestClient(app) as client:
        app.dependency_overrides[get_db] = lambda: db
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

    engine.dispose()
