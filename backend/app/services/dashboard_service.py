from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, or_, select

from app.models.alert import Alert
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment as Health
from app.models.fault_classification import FaultClassification as Fault
from app.models.inspection import Inspection
from app.models.sensor_reading import SensorReading as Reading
from app.services.equipment_monitoring_service import get_equipment_monitoring


def dashboard_overview(db, user_id):
    now = datetime.now(timezone.utc)
    equipment_ids = select(Equipment.id).where(Equipment.user_id == user_id)
    owned_inspections = select(Inspection.id).where(
        Inspection.user_id == user_id, Inspection.equipment_id.in_(equipment_ids)
    )
    equipment_counts = dict(db.execute(
        select(Equipment.status, func.count()).where(Equipment.user_id == user_id).group_by(Equipment.status)
    ).all())
    inspection_counts = dict(db.execute(
        owned_inspections.with_only_columns(Inspection.status, func.count()).group_by(Inspection.status)
    ).all())
    open_alerts = select(Alert).join(
        Inspection, (Inspection.id == Alert.inspection_id) & (Inspection.equipment_id == Alert.equipment_id)
    ).where(Inspection.user_id == user_id, Alert.equipment_id.in_(equipment_ids), Alert.status == "open")
    alert_counts = dict(db.execute(
        open_alerts.with_only_columns(Alert.severity, func.count()).group_by(Alert.severity)
    ).all())
    by_equipment = open_alerts.with_only_columns(
        Alert.equipment_id, func.count().label("open_count"),
    ).group_by(Alert.equipment_id).subquery()

    latest_execution = (
        select(Inspection.id).where(
            Inspection.equipment_id == Equipment.id, Inspection.user_id == user_id,
            Inspection.started_at.is_not(None),
        ).order_by(Inspection.started_at.desc(), Inspection.id.desc()).limit(1).correlate(Equipment).scalar_subquery()
    )
    assessment_inspection = Inspection.__table__.alias("assessment_inspection")
    latest_health = (
        select(Health.id).join(assessment_inspection, assessment_inspection.c.id == Health.inspection_id).where(
            Health.equipment_id == Equipment.id, assessment_inspection.c.equipment_id == Equipment.id,
            assessment_inspection.c.user_id == user_id, assessment_inspection.c.started_at.is_not(None),
            Health.assessed_at <= now,
        ).order_by(Health.assessed_at.desc(), Health.id.desc()).limit(1).correlate(Equipment).scalar_subquery()
    )
    health_counts = dict(db.execute(
        select(func.coalesce(Health.status, "not_evaluated"), func.count())
        .select_from(Equipment).outerjoin_from(Equipment, Health, Health.id == latest_health)
        .where(Equipment.user_id == user_id).group_by(Health.status)
    ).all())

    live_reading = select(Reading.id).where(
        Reading.equipment_id == Equipment.id, Reading.inspection_id == Inspection.id,
        Inspection.status == "active", Reading.timestamp >= now - timedelta(seconds=60), Reading.timestamp <= now,
        Reading.validation_status == "valid", Reading.value > float("-inf"), Reading.value < float("inf"),
    ).correlate(Equipment, Inspection)
    live_anomaly = live_reading.where(Reading.detection_status == "anomaly").exists()
    live_fault = live_reading.join(Fault, Fault.source_reading_id == Reading.id).where(Fault.status == "identified").exists()
    current_health_issue = (Health.inspection_id == Inspection.id) & Health.status.in_(["warning", "critical"])
    latest_equipment = (
        select(Equipment, Inspection)
        .select_from(Equipment)
        .outerjoin(Inspection, Inspection.id == latest_execution)
        .where(Equipment.user_id == user_id)
    )
    attention_rows = db.execute(
        latest_equipment.add_columns(
            Health.status, by_equipment.c.open_count, current_health_issue, live_anomaly, live_fault,
        ).outerjoin_from(Equipment, Health, Health.id == latest_health)
        .outerjoin_from(Equipment, by_equipment, by_equipment.c.equipment_id == Equipment.id)
        .where(or_(by_equipment.c.open_count.is_not(None), current_health_issue, live_anomaly, live_fault))
        .order_by(
            case((Health.status == "critical", 0), (Health.status == "warning", 1), else_=2),
            func.coalesce(by_equipment.c.open_count, 0).desc(), Equipment.id,
        ).limit(12)
    )
    attention = [
        {
            "equipment_id": equipment.id, "equipment_name": equipment.name,
            "inspection_id": inspection.id if inspection else None,
            "health_status": health or "not_evaluated", "open_alerts": open_count or 0,
            "reasons": [reason for present, reason in [
                (open_count, "Open alerts"), (health_issue, "Latest inspection health"),
                (anomaly, "Recent live anomaly"), (fault, "Recent live fault"),
            ] if present],
        }
        for equipment, inspection, health, open_count, health_issue, anomaly, fault in attention_rows
    ]

    activity_time = func.coalesce(Inspection.ended_at, Inspection.started_at, Inspection.created_at)
    recent = db.execute(
        select(
            Inspection.id, Inspection.equipment_id, Equipment.name.label("equipment_name"), Inspection.status,
            Inspection.scheduled_at, Inspection.started_at, Inspection.ended_at, activity_time.label("activity_at"),
        ).join(Equipment, Equipment.id == Inspection.equipment_id)
        .where(Equipment.user_id == user_id, Inspection.user_id == user_id)
        .order_by(case((Inspection.status == "active", 0), else_=1), activity_time.desc(), Inspection.id.desc()).limit(10)
    ).mappings().all()
    monitored = db.execute(
        latest_equipment.where(Inspection.id.is_not(None))
        .order_by(case((Inspection.status == "active", 0), else_=1), Inspection.started_at.desc(), Inspection.id.desc())
        .limit(6)
    ).all()

    return {
        "observed_at": now,
        "equipment": {"total": sum(equipment_counts.values()), "active": equipment_counts.get("active", 0),
                      "inactive": equipment_counts.get("inactive", 0)},
        "health": health_counts,
        "alerts": {"total": sum(alert_counts.values()), "warning": alert_counts.get("warning", 0),
                   "critical": alert_counts.get("critical", 0)},
        "inspections": inspection_counts,
        "attention": attention,
        "recent_inspections": recent,
        "monitoring": [get_equipment_monitoring(db, equipment) for equipment, _ in monitored],
    }
