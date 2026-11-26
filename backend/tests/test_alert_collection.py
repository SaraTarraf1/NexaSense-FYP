from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.alert import Alert
from app.models.alert_notification import AlertNotification
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment
from app.models.fault_classification import FaultClassification
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.services import alert_notification_service
from app.services.alert_notification_service import dispatch_pending_alert_notifications
from app.services.alert_service import record_collection_alerts
from app.services.sensor_collection_service import collect_inspection_readings
from app.services.sensor_configuration import SENSOR_DEFINITIONS
from app.services.sensor_scheduler import SensorScheduler
from app.services.sensor_simulator import SimulatedMeasurement


@pytest.fixture
def collection_database():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        Base.metadata.create_all(connection)

    try:
        with Session(engine, autoflush=False) as db:
            user = User(full_name="Alert test", email="alert-test@example.com", password_hash="unused")
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
            yield db, equipment, inspection
    finally:
        engine.dispose()


def simulate_values(monkeypatch, temperature, thermal, vibration):
    measurements = {"temperature": temperature, "thermal": thermal, "vibration": vibration}
    monkeypatch.setattr(
        "app.services.sensor_collection_service.simulate_sensor_reading",
        measurements.__getitem__,
    )


def test_collection_suppresses_repeats_per_inspection_and_diagnostic_rule(
    collection_database, monkeypatch
):
    db, equipment, inspection = collection_database
    simulate_values(
        monkeypatch,
        SimulatedMeasurement(90.0, "abnormal"),
        SimulatedMeasurement(145.0, "abnormal"),
        SimulatedMeasurement(20.0, "abnormal"),
    )
    first_cycle = datetime.now(timezone.utc)

    class CollectionClock:
        current = first_cycle

        @classmethod
        def now(cls, tz):
            return cls.current.astimezone(tz)

    monkeypatch.setattr("app.services.sensor_collection_service.datetime", CollectionClock)
    reading_ids = {reading.id for reading in collect_inspection_readings(db, inspection.id)}
    db.commit()
    first_alerts = db.scalars(select(Alert)).all()
    assert {alert.event_key: alert.severity for alert in first_alerts} == {
        "anomaly:temperature:above_threshold": "warning",
        "anomaly:thermal:above_threshold": "warning",
        "anomaly:vibration:above_threshold": "warning",
        "fault:DR-001": "critical",
        "fault:DR-002": "warning",
        "health:critical": "critical",
    }
    assert len(first_alerts) == 6
    for alert in first_alerts:
        assert set(alert.evidence_reading_ids) <= reading_ids
        if alert.event_type == "fault":
            assert len(alert.evidence_reading_ids) == 2
            assert alert.fault_classification_id == alert.source_reading_id
        if alert.event_type == "health":
            assessment = db.get(EquipmentHealthAssessment, alert.health_assessment_id)
            assert assessment.status == "critical"
            assert alert.source_reading_id == assessment.trigger_reading_id
            assert alert.evidence_reading_ids == assessment.evidence_reading_ids
            assert alert.fault_classification_id is None
    notifications = db.scalars(select(AlertNotification)).all()
    assert {notification.alert_id for notification in notifications} == {
        alert.id for alert in first_alerts
    }
    assert len(notifications) == len(first_alerts)
    assert all(
        (notification.recipient_user_id, notification.channel, notification.status)
        == (equipment.user_id, "in_app", "pending")
        for notification in notifications
    )

    CollectionClock.current = first_cycle + timedelta(seconds=30)
    assert len(collect_inspection_readings(db, inspection.id)) == 3
    db.commit()
    assert len(db.scalars(select(Alert)).all()) == 6

    CollectionClock.current = first_cycle + timedelta(seconds=60)
    assert len(collect_inspection_readings(db, inspection.id)) == 3
    db.commit()
    assert len(db.scalars(select(Alert)).all()) == 12

    reading_types = {sensor.id: sensor.sensor_type for sensor in db.scalars(select(Sensor))}
    original_readings = [db.get(SensorReading, reading_id) for reading_id in sorted(reading_ids)]
    original_classifications = db.scalars(
        select(FaultClassification).where(FaultClassification.source_reading_id.in_(reading_ids))
    ).all()
    record_collection_alerts(
        db, equipment=equipment, inspection=inspection, readings=original_readings,
        sensor_types=reading_types, classifications=original_classifications,
        now=first_cycle + timedelta(seconds=120),
        health_assessment=assessment,
    )
    db.commit()
    assert len(db.scalars(select(Alert)).all()) == 12

    inspection.status = "completed"
    new_inspection = Inspection(equipment_id=equipment.id, user_id=equipment.user_id)
    db.add(new_inspection)
    db.flush()
    assert len(collect_inspection_readings(db, new_inspection.id)) == 3
    db.commit()
    assert len(db.scalars(select(Alert).where(Alert.inspection_id == new_inspection.id)).all()) == 6
    assert len(db.scalars(select(AlertNotification)).all()) == 18


@pytest.mark.parametrize(
    ("temperature", "thermal", "expected_keys"),
    [
        (SimulatedMeasurement(35.0, "normal"), SimulatedMeasurement(50.0, "normal"), set()),
        (SimulatedMeasurement(999.0, "invalid"), SimulatedMeasurement(None, "missing"), set()),
        (
            SimulatedMeasurement(90.0, "abnormal"),
            SimulatedMeasurement(50.0, "normal"),
            {"anomaly:temperature:above_threshold", "fault:unknown", "health:warning"},
        ),
        (
            SimulatedMeasurement(90.0, "abnormal"),
            SimulatedMeasurement(None, "missing"),
            {"anomaly:temperature:above_threshold", "fault:undetermined"},
        ),
    ],
)
def test_collection_only_alerts_on_eligible_results(
    collection_database, monkeypatch, temperature, thermal, expected_keys
):
    db, _, inspection = collection_database
    simulate_values(monkeypatch, temperature, thermal, SimulatedMeasurement(2.0, "normal"))
    collect_inspection_readings(db, inspection.id)
    db.commit()

    alerts = db.scalars(select(Alert)).all()
    assert {alert.event_key for alert in alerts} == expected_keys
    assert all(alert.severity == "warning" for alert in alerts)
    if "fault:undetermined" in expected_keys:
        assert next(alert for alert in alerts if alert.event_type == "fault").description.endswith(
            "Needed readings: thermal."
        )
    assert len(db.scalars(select(AlertNotification)).all()) == len(expected_keys)


def run_scheduler_tick(monkeypatch, db):
    test_sessions = sessionmaker(bind=db.get_bind(), autoflush=False)
    monkeypatch.setattr("app.services.sensor_scheduler.SessionLocal", test_sessions)
    scheduler = SensorScheduler()
    monkeypatch.setattr(scheduler._stop_event, "wait", lambda _: scheduler._stop_event.set())
    scheduler._run()


def simulate_one_anomaly(monkeypatch):
    simulate_values(
        monkeypatch,
        SimulatedMeasurement(90.0, "abnormal"),
        SimulatedMeasurement(None, "missing"),
        SimulatedMeasurement(2.0, "normal"),
    )


def test_scheduler_records_failed_and_successful_deliveries(collection_database, monkeypatch):
    db, _, _ = collection_database
    simulate_one_anomaly(monkeypatch)
    publish = alert_notification_service._publish_in_app
    attempts = []

    def publish_with_failure(notification, equipment_owner_id, recipient_is_active):
        attempts.append(notification.id)
        if len(attempts) == 1:
            raise RuntimeError("Simulated in-app delivery failure")
        publish(notification, equipment_owner_id, recipient_is_active)

    monkeypatch.setattr(alert_notification_service, "_publish_in_app", publish_with_failure)
    run_scheduler_tick(monkeypatch, db)

    notifications = db.scalars(select(AlertNotification).order_by(AlertNotification.id)).all()
    assert [record.status for record in notifications] == ["failed", "delivered"]
    assert notifications[0].error_message == "In-app notification delivery failed."
    assert notifications[1].error_message is None
    assert all(record.attempted_at is not None for record in notifications)
    assert [alert.status for alert in db.scalars(select(Alert))] == ["open", "open"]

    dispatch_pending_alert_notifications(db)
    assert attempts == [record.id for record in notifications]


def test_dispatch_recovers_committed_alerts_after_a_failed_batch(collection_database, monkeypatch):
    db, _, inspection = collection_database
    simulate_one_anomaly(monkeypatch)

    def fail_after_dispatch(worker_db):
        dispatch_pending_alert_notifications(worker_db)
        worker_db.flush()
        raise RuntimeError("Simulated delivery transaction failure")

    with monkeypatch.context() as failing_dispatch:
        failing_dispatch.setattr(
            "app.services.sensor_scheduler.dispatch_pending_alert_notifications",
            fail_after_dispatch,
        )
        run_scheduler_tick(failing_dispatch, db)

    assert len(db.scalars(select(Alert)).all()) == 2
    notifications = db.scalars(select(AlertNotification)).all()
    assert all(record.status == "pending" and record.attempted_at is None for record in notifications)
    inspection.status = "completed"
    db.commit()

    run_scheduler_tick(monkeypatch, db)
    assert [record.status for record in db.scalars(select(AlertNotification))] == [
        "delivered", "delivered"
    ]


def test_dispatch_rechecks_the_recipient_and_channel(collection_database, monkeypatch):
    db, _, inspection = collection_database
    simulate_one_anomaly(monkeypatch)
    collect_inspection_readings(db, inspection.id)
    db.flush()
    wrong_owner, unavailable_channel = db.scalars(
        select(AlertNotification).order_by(AlertNotification.id)
    ).all()
    other_user = User(full_name="Other user", email="other@example.com", password_hash="unused")
    db.add(other_user)
    db.flush()
    wrong_owner.recipient_user_id = other_user.id
    unavailable_channel.channel = "unavailable"
    db.commit()

    dispatch_pending_alert_notifications(db)
    db.commit()
    assert wrong_owner.status == "failed"
    assert wrong_owner.error_message == "The recipient is no longer eligible for this alert."
    assert unavailable_channel.status == "failed"
    assert unavailable_channel.error_message == "The configured notification channel is unavailable."


def test_health_alert_escalation_is_not_suppressed_by_a_recent_warning(
    collection_database, monkeypatch
):
    db, _, inspection = collection_database
    measurements = {
        "temperature": SimulatedMeasurement(90.0, "abnormal"),
        "thermal": SimulatedMeasurement(50.0, "normal"),
        "vibration": SimulatedMeasurement(2.0, "normal"),
    }

    class CollectionClock:
        current = datetime.now(timezone.utc)

        @classmethod
        def now(cls, tz):
            return cls.current.astimezone(tz)

    monkeypatch.setattr("app.services.sensor_collection_service.datetime", CollectionClock)
    monkeypatch.setattr(
        "app.services.sensor_collection_service.simulate_sensor_reading",
        measurements.__getitem__,
    )
    health_alerts = select(Alert).where(Alert.event_type == "health").order_by(Alert.id)

    collect_inspection_readings(db, inspection.id)
    db.commit()
    assert [alert.severity for alert in db.scalars(health_alerts)] == ["warning"]

    CollectionClock.current += timedelta(seconds=6)
    measurements["thermal"] = SimulatedMeasurement(145.0, "abnormal")
    collect_inspection_readings(db, inspection.id)
    db.commit()
    assert [alert.severity for alert in db.scalars(health_alerts)] == ["warning", "critical"]

    CollectionClock.current += timedelta(seconds=6)
    collect_inspection_readings(db, inspection.id)
    db.commit()
    assert [alert.severity for alert in db.scalars(health_alerts)] == ["warning", "critical"]
