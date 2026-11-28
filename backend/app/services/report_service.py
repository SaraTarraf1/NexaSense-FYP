from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

from app.models.alert import Alert
from app.models.equipment import Equipment
from app.models.equipment_health_assessment import EquipmentHealthAssessment as Health
from app.models.fault_classification import FaultClassification as Fault
from app.models.inspection import Inspection
from app.models.inspection_report import InspectionReport
from app.models.sensor_reading import SensorReading as Reading
from app.schemas.report import ReportSnapshot
from app.services.history_service import History, reading_detail


FAULT_ACTIONS = {
    "overheating": "Inspect ventilation, cooling components and operating conditions.",
    "mechanical_stress": "Inspect mechanical components, mounting and alignment.",
    "electrical_overheating": "Arrange a qualified electrical inspection of the equipment and its cooling.",
    "pump_mechanical_fault": "Inspect the pump mounting, coupling, bearings and operating conditions.",
    "ventilation_mechanical_fault": "Inspect the fan, drive, mounting and airflow path.",
    "heating_system_overheating": "Inspect the heating system controls, heat transfer and ventilation.",
}


def maintenance_actions(faults, health_status):
    actions = []
    for fault in faults:
        if fault["status"] == "unknown":
            actions.append("Arrange a technical inspection to investigate the anomaly.")
        elif fault["status"] == "undetermined":
            actions.append("Collect the missing measurements and reassess the equipment.")
        for match in fault["matches"]:
            action = FAULT_ACTIONS.get(match["fault_type"])
            if action:
                actions.append(action)

    if health_status in {"insufficient_data", "not_evaluated"}:
        actions.append("Complete the required measurements and review the next health assessment.")
    elif health_status == "normal":
        actions.append("Continue routine preventive maintenance.")
    elif health_status in {"warning", "critical"}:
        actions.append("Prioritize review by a qualified maintenance technician."
                       if health_status == "critical" else "Schedule a maintenance review.")
    return list(dict.fromkeys(actions))


def owned_reports(user_id):
    return (
        select(InspectionReport)
        .join(Equipment, Equipment.id == InspectionReport.equipment_id)
        .join(Inspection, Inspection.id == InspectionReport.inspection_id)
        .where(
            InspectionReport.user_id == user_id, Equipment.user_id == user_id,
            Inspection.user_id == user_id, Inspection.equipment_id == Equipment.id,
        )
    )


def equipment_for_report(db, equipment_id, user_id):
    equipment = db.scalar(select(Equipment).where(Equipment.id == equipment_id, Equipment.user_id == user_id))
    if equipment is None:
        raise HTTPException(404, "Equipment not found.")
    return equipment


def save_report(db, equipment_id, inspection_id, user_id):
    equipment = equipment_for_report(db, equipment_id, user_id)
    # Serializes repeated generation for the same inspection in PostgreSQL.
    inspection = db.scalar(select(Inspection).where(
        Inspection.id == inspection_id, Inspection.equipment_id == equipment.id,
        Inspection.user_id == user_id,
    ).with_for_update())
    if inspection is None:
        raise HTTPException(404, "Inspection not found for this equipment.")
    if inspection.status != "completed":
        raise HTTPException(409, "Reports require a completed inspection.")
    saved = db.scalar(owned_reports(user_id).where(InspectionReport.inspection_id == inspection.id))
    if saved is not None:
        return saved

    history = History(db, equipment.id, user_id, inspection_id=inspection.id)
    readings = [
        reading_detail(reading, sensor_type)
        for reading, sensor_type in db.execute(history.readings.order_by(Reading.timestamp, Reading.id))
    ]
    faults = history.fault_details(db.execute(history.faults.order_by(Fault.classified_at, Reading.id)))
    health = db.scalars(history.health.order_by(Health.assessed_at, Health.id)).all()
    alerts = db.scalars(select(Alert).where(
        Alert.equipment_id == equipment.id, Alert.inspection_id == inspection.id,
    ).order_by(Alert.created_at, Alert.id)).all()
    health_status = health[-1].status if health else "not_evaluated"
    stats = history.statistics()
    limitations = []
    if not stats:
        limitations.append("No valid finite sensor measurements were saved.")
    if any(reading.value is None or reading.validation_status != "valid" for reading in readings):
        limitations.append("Invalid or missing measurements are excluded from statistics.")
    if health_status in {"insufficient_data", "not_evaluated"}:
        limitations.append("A conclusive health assessment was unavailable at generation time.")
    duration = (
        (inspection.ended_at - inspection.started_at).total_seconds()
        if inspection.started_at and inspection.ended_at else None
    )
    if duration is None:
        limitations.append("The execution duration could not be determined from stored timestamps.")
    snapshot = ReportSnapshot(
        equipment=equipment, inspection=inspection, duration_seconds=duration, health_status=health_status,
        readings=readings, statistics=stats,
        anomalies=[reading for reading in readings if reading.detection_status == "anomaly"],
        faults=faults, health=health, alerts=alerts, recommendations=maintenance_actions(faults, health_status),
        limitations=limitations,
    )
    report = InspectionReport(
        user_id=user_id, equipment_id=equipment.id, inspection_id=inspection.id,
        generated_at=datetime.now(timezone.utc), snapshot=snapshot.model_dump(mode="json"),
    )
    db.add(report)
    db.flush()
    return report


def describe_report(report):
    snapshot = report.snapshot
    inspection = snapshot["inspection"]
    generated_at = report.generated_at
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return {
        "id": report.id, "equipment_id": report.equipment_id, "equipment_name": snapshot["equipment"]["name"],
        "inspection_id": report.inspection_id, "inspection_date": inspection["started_at"] or inspection["scheduled_at"],
        "generated_at": generated_at, "health_status": snapshot["health_status"],
    }
