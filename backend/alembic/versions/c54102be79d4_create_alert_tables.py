"""Create alerts and in-app notification delivery records."""

from alembic import op
import sqlalchemy as sa


revision = "c54102be79d4"
down_revision = "a614ef710b23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "equipment_id", sa.Integer(),
            sa.ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "inspection_id", sa.Integer(),
            sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "source_reading_id", sa.Integer(),
            sa.ForeignKey("sensor_readings.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "fault_classification_id", sa.Integer(),
            sa.ForeignKey("fault_classifications.source_reading_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("event_key", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("evidence_reading_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.CheckConstraint("severity IN ('warning', 'critical')", name="ck_alert_severity"),
        sa.CheckConstraint(
            "(event_type = 'anomaly' AND fault_classification_id IS NULL) OR "
            "(event_type = 'fault' AND fault_classification_id IS NOT NULL "
            "AND fault_classification_id = source_reading_id)",
            name="ck_alert_event_source",
        ),
        sa.UniqueConstraint("source_reading_id", "event_key", name="uq_alert_trigger"),
    )
    op.create_index(
        "ix_alerts_duplicate_lookup", "alerts",
        ["equipment_id", "inspection_id", "event_key", "created_at"],
    )
    op.create_index("ix_alerts_equipment_created_at", "alerts", ["equipment_id", "created_at"])

    op.create_table(
        "alert_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "alert_id", sa.Integer(),
            sa.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "recipient_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("channel", sa.String(20), server_default="in_app", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status = 'pending' AND attempted_at IS NULL AND error_message IS NULL) OR "
            "(status = 'delivered' AND attempted_at IS NOT NULL AND error_message IS NULL) OR "
            "(status = 'failed' AND attempted_at IS NOT NULL AND error_message IS NOT NULL)",
            name="ck_alert_notification_outcome",
        ),
        sa.UniqueConstraint(
            "alert_id", "recipient_user_id", "channel", name="uq_alert_notification_recipient",
        ),
    )
    op.create_index("ix_alert_notifications_dispatch", "alert_notifications", ["status", "id"])


def downgrade() -> None:
    op.drop_table("alert_notifications")
    op.drop_table("alerts")
