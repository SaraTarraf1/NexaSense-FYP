from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Inspection(Base):
    __tablename__ = "inspections"
    __table_args__ = (
        Index(
            "uq_inspection_schedule_slot",
            "equipment_id",
            "scheduled_at",
            unique=True,
            postgresql_where=text("status <> 'cancelled' OR started_at IS NOT NULL"),
            sqlite_where=text("status <> 'cancelled' OR started_at IS NOT NULL"),
        ),
        Index("ix_inspections_due_reminders", "status", "ready_reminded_at", "scheduled_at"),
        CheckConstraint(
            "(status = 'scheduled' AND scheduled_at IS NOT NULL "
            "AND started_at IS NULL AND ended_at IS NULL) OR "
            "(status = 'cancelled' AND scheduled_at IS NOT NULL "
            "AND started_at IS NULL AND ended_at IS NOT NULL) OR "
            "(status <> 'scheduled' AND started_at IS NOT NULL)",
            name="ck_inspection_execution_times",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    equipment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="active",
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ready_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).evaluates_none(),
        nullable=True,
        server_default=func.now(),
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
