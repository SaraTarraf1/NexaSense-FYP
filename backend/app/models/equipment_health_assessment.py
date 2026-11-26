from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EquipmentHealthAssessment(Base):
    __tablename__ = "equipment_health_assessments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('normal', 'warning', 'critical', 'insufficient_data')",
            name="ck_equipment_health_assessment_status",
        ),
        UniqueConstraint("trigger_reading_id", name="uq_equipment_health_assessment_trigger"),
        Index("ix_equipment_health_assessment_history", "equipment_id", "assessed_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_reading_id: Mapped[int] = mapped_column(
        ForeignKey("sensor_readings.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_reading_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    fault_rule_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    missing_sensor_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
