from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InspectionReport(Base):
    __tablename__ = "inspection_reports"
    __table_args__ = (
        UniqueConstraint("inspection_id", name="uq_inspection_report_inspection"),
        Index("ix_inspection_reports_owner_created", "user_id", "generated_at", "id"),
        Index("ix_inspection_reports_equipment_id", "equipment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
