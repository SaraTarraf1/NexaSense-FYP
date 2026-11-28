from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.sensor_readings import serialize_reading
from app.models.equipment_health_assessment import EquipmentHealthAssessment as Health
from app.models.fault_classification import FaultClassification as Fault
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading as Reading
from app.schemas.history import HistoryInspection, HistoryReading
from app.schemas.inspection import InspectionResponse


def count_rows(db, query):
    return db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))


def reading_detail(reading, sensor_type):
    return HistoryReading(
        **serialize_reading(reading, sensor_type).model_dump(),
        detection_status=reading.detection_status,
        anomaly_type=reading.anomaly_type,
        detection_message=reading.detection_message,
    )


def occurrences(counts, denominator):
    return [
        {"type": label, "count": count, "frequency": count / denominator}
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


class History:
    def __init__(self, db: Session, equipment_id: int, user_id: int, *, bounds=None, inspection_id=None):
        self.db = db
        self.inspections = select(Inspection).where(
            Inspection.equipment_id == equipment_id, Inspection.user_id == user_id
        )
        if inspection_id is not None:
            self.inspections = self.inspections.where(Inspection.id == inspection_id)
        owned_ids = self.inspections.with_only_columns(Inspection.id)
        self.readings = select(Reading, Sensor.sensor_type).join(Sensor).where(
            Reading.equipment_id == equipment_id, Reading.inspection_id.in_(owned_ids)
        )
        self.evidence = self.readings
        self.health = select(Health).where(
            Health.equipment_id == equipment_id, Health.inspection_id.in_(owned_ids)
        )
        self.inspection_time = func.coalesce(Inspection.started_at, Inspection.scheduled_at, Inspection.created_at)
        self.faults = self.readings.join(Fault, Fault.source_reading_id == Reading.id).add_columns(Fault)
        if bounds:
            start, end = bounds
            self.readings = self.readings.where(Reading.timestamp >= start, Reading.timestamp < end)
            self.faults = self.faults.where(Fault.classified_at >= start, Fault.classified_at < end)
            self.health = self.health.where(Health.assessed_at >= start, Health.assessed_at < end)
            self.inspections = self.inspections.where(self.inspection_time >= start, self.inspection_time < end)
        self.anomalies = self.readings.where(Reading.detection_status == "anomaly")
        self.valid = self.readings.where(
            Reading.validation_status == "valid",
            Reading.value > float("-inf"),
            Reading.value < float("inf"),
        )

    def statistics(self, include_points=False):
        groups = self.db.execute(
            self.valid.with_only_columns(
                Sensor.sensor_type, Reading.unit, func.min(Reading.value).label("minimum"),
                func.max(Reading.value).label("maximum"), func.avg(Reading.value).label("average"),
                func.count().label("count"),
            ).group_by(Sensor.sensor_type, Reading.unit).order_by(Sensor.sensor_type, Reading.unit)
        ).mappings()
        stats = [dict(group) for group in groups]
        if include_points:
            for group in stats:
                stride = max(1, (group["count"] - 1 + 198) // 199)
                ranked = self.valid.where(
                    Sensor.sensor_type == group["sensor_type"], Reading.unit == group["unit"]
                ).with_only_columns(
                    Reading.timestamp, Reading.value,
                    func.row_number().over(order_by=(Reading.timestamp, Reading.id)).label("position"),
                ).subquery()
                group["points"] = self.db.execute(
                    select(ranked.c.timestamp, ranked.c.value).where(
                        ((ranked.c.position - 1) % stride == 0) | (ranked.c.position == group["count"])
                    ).order_by(ranked.c.position)
                ).mappings().all()
        return stats

    def summary(self):
        stats = self.statistics(include_points=True)
        anomalies = dict(self.db.execute(
            self.anomalies.with_only_columns(Reading.anomaly_type, func.count()).group_by(Reading.anomaly_type)
        ).all())
        anomaly_count = sum(anomalies.values())
        faults = Counter()
        fault_count = 0
        fault_rows = self.faults.with_only_columns(Fault.status, Fault.matches).execution_options(yield_per=500)
        for status, matches in self.db.execute(fault_rows):
            fault_count += 1
            faults.update({match["fault_type"] for match in matches} or {status})
        return {
            "inspections": count_rows(self.db, self.inspections),
            "valid_measurements": sum(group["count"] for group in stats),
            "anomalies": anomaly_count,
            "faults": fault_count,
            "health_assessments": count_rows(self.db, self.health),
            "sensors": stats,
            "anomaly_types": occurrences({label or "unspecified": count for label, count in anomalies.items()}, anomaly_count),
            "fault_types": occurrences(faults, fault_count),
        }

    def fault_details(self, rows):
        rows = list(rows)
        evidence_ids = {
            identity for _, _, fault in rows for match in fault.matches for identity in match["evidence_reading_ids"]
        }
        evidence = {}
        if evidence_ids:
            evidence = {
                (reading.inspection_id, reading.id): reading_detail(reading, sensor_type)
                for reading, sensor_type in self.db.execute(self.evidence.where(Reading.id.in_(evidence_ids)))
            }
        return [
            {
                "source_reading": reading_detail(reading, sensor_type),
                "classified_at": fault.classified_at,
                "status": fault.status,
                "message": fault.message,
                "missing_sensor_types": fault.missing_sensor_types,
                "matches": [
                    {**match, "evidence": [
                        evidence[(reading.inspection_id, identity)]
                        for identity in match["evidence_reading_ids"]
                        if (reading.inspection_id, identity) in evidence
                    ]}
                    for match in fault.matches
                ],
            }
            for reading, sensor_type, fault in rows
        ]

    def page(self, section, offset, limit):
        db = self.db
        if section == "inspections":
            latest = self.health.with_only_columns(Health.status).where(
                Health.inspection_id == Inspection.id
            ).order_by(Health.assessed_at.desc(), Health.id.desc()).limit(1).scalar_subquery()
            query = self.inspections.add_columns(func.coalesce(latest, "not_evaluated")).order_by(
                self.inspection_time, Inspection.id
            )
        elif section == "health":
            query = self.health.order_by(Health.assessed_at, Health.id)
        elif section == "faults":
            query = self.faults.order_by(Fault.classified_at, Reading.id)
        else:
            query = (self.anomalies if section == "anomalies" else self.readings).order_by(Reading.timestamp, Reading.id)

        total = count_rows(db, query)
        rows = db.execute(query.offset(offset).limit(limit))
        if section == "inspections":
            items = [
                HistoryInspection(**InspectionResponse.model_validate(inspection).model_dump(), health_status=status)
                for inspection, status in rows
            ]
        elif section == "health":
            items = rows.scalars().all()
        elif section == "faults":
            items = self.fault_details(rows)
        else:
            items = [reading_detail(reading, sensor_type) for reading, sensor_type in rows]
        return {"items": items, "total": total, "offset": offset, "limit": limit}
