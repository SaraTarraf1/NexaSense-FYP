from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlertNotification(Base):
    __tablename__ = "alert_notifications"
    __table_args__ = (
        CheckConstraint(
            "(status = 'pending' AND attempted_at IS NULL AND error_message IS NULL) OR "
            "(status = 'delivered' AND attempted_at IS NOT NULL AND error_message IS NULL) OR "
            "(status = 'failed' AND attempted_at IS NOT NULL AND error_message IS NOT NULL)",
            name="ck_alert_notification_outcome",
        ),
        UniqueConstraint(
            "alert_id", "recipient_user_id", "channel", name="uq_alert_notification_recipient"
        ),
        Index("ix_alert_notifications_dispatch", "status", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), server_default="in_app", nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
