
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    __table_args__ = (
        CheckConstraint(
            "validation_status IN ('valid', 'invalid', 'missing')",
            name="ck_sensor_reading_validation_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    sensor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sensors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    equipment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    inspection_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    validation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    validation_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
