
from sqlalchemy import (
    Boolean,
    Float,
    Integer,
    String,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Sensor(Base):
    __tablename__ = "sensors"

    __table_args__ = (
        CheckConstraint(
            "min_value < max_value",
            name="ck_sensor_valid_limits",
        ),
        CheckConstraint(
            "collection_interval_seconds > 0",
            name="ck_sensor_positive_interval",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    sensor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    min_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    max_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    collection_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
