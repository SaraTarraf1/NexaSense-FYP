from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.services.sensor_collection_service import collect_inspection_readings
from app.services.sensor_configuration import SENSOR_DEFINITIONS
from app.services.sensor_simulator import SimulatedMeasurement


def test_collection_stores_health_history_and_rolls_back_with_readings(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        Base.metadata.create_all(connection)

    class CollectionClock:
        current = datetime.now(timezone.utc)

        @classmethod
        def now(cls, tz):
            return cls.current.astimezone(tz)

    monkeypatch.setattr("app.services.sensor_collection_service.datetime", CollectionClock)
    try:
        with Session(engine, autoflush=False) as db:
            user = User(full_name="Health test", email="health-test@example.com", password_hash="unused")
            db.add(user)
            db.flush()
            equipment = Equipment(
                user_id=user.id, identifier="AC1", name="Test AC",
                equipment_type="Air conditioner", location="Test",
            )
            db.add(equipment)
            db.add_all([
                Sensor(sensor_type=kind, **definition)
                for kind, definition in SENSOR_DEFINITIONS.items()
            ])
            db.flush()
            inspection = Inspection(equipment_id=equipment.id, user_id=user.id)
            db.add(inspection)
            db.commit()
            inspection_id = inspection.id
            history = (
                select(EquipmentHealthAssessment)
                .where(EquipmentHealthAssessment.inspection_id == inspection_id)
                .order_by(EquipmentHealthAssessment.id)
            )

            measurements = {
                "temperature": SimulatedMeasurement(90.0, "abnormal"),
                "thermal": SimulatedMeasurement(145.0, "abnormal"),
                "vibration": SimulatedMeasurement(2.0, "normal"),
            }
            monkeypatch.setattr(
                "app.services.sensor_collection_service.simulate_sensor_reading",
                measurements.__getitem__,
            )
            first = collect_inspection_readings(db, inspection_id)
            first_ids = {reading.id for reading in first}
            db.commit()
            (critical,) = db.scalars(history).all()
            assert critical.status == "critical"
            assert critical.fault_rule_ids == ["DR-001"]
            assert set(critical.evidence_reading_ids) == first_ids
            assert critical.trigger_reading_id == first[-1].id

            assert collect_inspection_readings(db, inspection_id) == []
            db.commit()
            assert len(db.scalars(history).all()) == 1

            CollectionClock.current += timedelta(seconds=6)
            measurements["temperature"] = SimulatedMeasurement(35.0, "normal")
            measurements["thermal"] = SimulatedMeasurement(50.0, "normal")
            collect_inspection_readings(db, inspection_id)
            db.commit()
            assert [record.status for record in db.scalars(history)] == ["critical", "normal"]

            CollectionClock.current += timedelta(seconds=6)
            measurements["thermal"] = SimulatedMeasurement(None, "missing")
            collect_inspection_readings(db, inspection_id)
            db.flush()
            pending = db.scalars(history).all()[-1]
            assert pending.status == "insufficient_data"
            assert pending.missing_sensor_types == ["thermal"]
            assert len(pending.evidence_reading_ids) == 2
            db.rollback()
            assert [record.status for record in db.scalars(history)] == ["critical", "normal"]
            assert len(db.scalars(select(SensorReading)).all()) == 6

            collect_inspection_readings(db, inspection_id)
            db.commit()
            assert [record.status for record in db.scalars(history)] == [
                "critical", "normal", "insufficient_data"
            ]
    finally:
        engine.dispose()
