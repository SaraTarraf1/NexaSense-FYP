from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FaultClassification(Base):
    __tablename__ = "fault_classifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('identified', 'unknown', 'undetermined')",
            name="ck_fault_classification_status",
        ),
    )

    source_reading_id: Mapped[int] = mapped_column(
        ForeignKey("sensor_readings.id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    matches: Mapped[list[dict[str, str | list[int]]]] = mapped_column(JSON, nullable=False)
    missing_sensor_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
