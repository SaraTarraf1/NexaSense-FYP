import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.equipment import Equipment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.services.sensor_collection_service import collect_inspection_readings
from app.services.sensor_configuration import SENSOR_DEFINITIONS
from app.services.sensor_reading_service import save_sensor_reading
from app.services.sensor_simulator import SimulatedMeasurement


@pytest.mark.parametrize(
    ("temperature", "thermal", "expected_status", "expected_total"),
    [
        (90.0, 145.0, "identified", 2),
        (90.0, 50.0, "unknown", 1),
        (90.0, None, "undetermined", 1),
        (35.0, 50.0, None, 0),
        (999.0, 50.0, None, 0),
    ],
)
def test_collection_saves_fault_classifications_with_their_readings(
    monkeypatch, temperature, thermal, expected_status, expected_total
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        equipment = Equipment(
            user_id=1,
            identifier="AC1",
            name="Server Room AC",
            equipment_type="Air conditioner",
            location="Server Room",
        )
        sensors = {
            kind: Sensor(sensor_type=kind, **definition)
            for kind, definition in SENSOR_DEFINITIONS.items()
        }
        db.add_all([equipment, *sensors.values()])
        db.flush()

        previous = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(previous)
        db.flush()
        previous_reading = save_sensor_reading(db, previous.id, "thermal", 145.0)
        previous_id = previous_reading.id
        previous.status = "completed"
        active = Inspection(equipment_id=equipment.id, user_id=1)
        db.add(active)
        db.flush()
        inspection_id = active.id
        sensor_types = {sensor.id: kind for kind, sensor in sensors.items()}
        db.commit()

    values = {"temperature": temperature, "thermal": thermal, "vibration": 2.0}

    def simulate(kind):
        value = values[kind]
        return SimulatedMeasurement(value, "missing" if value is None else "normal")

    monkeypatch.setattr(
        "app.services.sensor_collection_service.simulate_sensor_reading",
        simulate,
    )
    with Session(engine) as db:
        collected = collect_inspection_readings(db, inspection_id)
        reading_ids = {sensor_types[reading.sensor_id]: reading.id for reading in collected}
        assert set(reading_ids) == set(values)
        db.commit()

    with Session(engine) as db:
        results = db.scalars(select(FaultClassification)).all()
        assert len(results) == expected_total
        assert db.get(FaultClassification, previous_id) is None
        assert db.get(FaultClassification, reading_ids["vibration"]) is None
        classification = db.get(FaultClassification, reading_ids["temperature"])
        if expected_status is None:
            assert classification is None
        else:
            assert classification.status == expected_status
            if expected_status == "identified":
                assert classification.matches == [{
                    "rule_id": "DR-001",
                    "fault_type": "overheating",
                    "evidence_reading_ids": [reading_ids["temperature"], reading_ids["thermal"]],
                }]
            if expected_status == "undetermined":
                assert classification.matches == []
                assert classification.missing_sensor_types == ["thermal"]

    engine.dispose()


def test_rolling_back_collection_discards_readings_and_pending_classifications(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        equipment = Equipment(
            user_id=1,
            identifier="EP1",
            name="Electrical Panel",
            equipment_type="Electrical panel",
            location="Server Room",
        )
        db.add(equipment)
        db.flush()
        inspection = Inspection(equipment_id=equipment.id, user_id=1)
        db.add_all([
            inspection,
            Sensor(sensor_type="temperature", **SENSOR_DEFINITIONS["temperature"]),
            Sensor(sensor_type="thermal", **SENSOR_DEFINITIONS["thermal"]),
        ])
        db.flush()
        inspection_id = inspection.id
        db.commit()

        values = {"temperature": 90.0, "thermal": 145.0}
        monkeypatch.setattr(
            "app.services.sensor_collection_service.simulate_sensor_reading",
            lambda kind: SimulatedMeasurement(values[kind], "abnormal"),
        )
        collect_inspection_readings(db, inspection_id)
        db.flush()
        assert len(db.scalars(select(FaultClassification)).all()) == 2
        db.rollback()
        assert db.scalars(select(SensorReading)).all() == []
        assert db.scalars(select(FaultClassification)).all() == []

    engine.dispose()
