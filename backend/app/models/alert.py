from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('warning', 'critical')",
            name="ck_alert_severity",
        ),
        CheckConstraint(
            "(event_type = 'anomaly' AND fault_classification_id IS NULL "
            "AND health_assessment_id IS NULL) OR "
            "(event_type = 'fault' AND fault_classification_id IS NOT NULL "
            "AND fault_classification_id = source_reading_id AND health_assessment_id IS NULL) OR "
            "(event_type = 'health' AND health_assessment_id IS NOT NULL "
            "AND fault_classification_id IS NULL)",
            name="ck_alert_event_source",
        ),
        UniqueConstraint("source_reading_id", "event_key", name="uq_alert_trigger"),
        Index(
            "ix_alerts_duplicate_lookup",
            "equipment_id",
            "inspection_id",
            "event_key",
            "created_at",
        ),
        Index("ix_alerts_equipment_created_at", "equipment_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    source_reading_id: Mapped[int] = mapped_column(
        ForeignKey("sensor_readings.id", ondelete="CASCADE"), nullable=False
    )
    fault_classification_id: Mapped[int | None] = mapped_column(
        ForeignKey("fault_classifications.source_reading_id", ondelete="CASCADE")
    )
    health_assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "equipment_health_assessments.id",
            name="fk_alerts_health_assessment_id",
            ondelete="CASCADE",
        )
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    event_key: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default="open", nullable=False)
    evidence_reading_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
