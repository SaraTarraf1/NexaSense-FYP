"""Link alerts to warning and critical equipment health assessments."""

from alembic import op
import sqlalchemy as sa


revision = "86bf9c3bb4a2"
down_revision = "731dc28f45ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("health_assessment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_alerts_health_assessment_id",
        "alerts", "equipment_health_assessments",
        ["health_assessment_id"], ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("ck_alert_event_source", "alerts", type_="check")
    op.create_check_constraint(
        "ck_alert_event_source",
        "alerts",
        "(event_type = 'anomaly' AND fault_classification_id IS NULL "
        "AND health_assessment_id IS NULL) OR "
        "(event_type = 'fault' AND fault_classification_id IS NOT NULL "
        "AND fault_classification_id = source_reading_id AND health_assessment_id IS NULL) OR "
        "(event_type = 'health' AND health_assessment_id IS NOT NULL "
        "AND fault_classification_id IS NULL)",
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM alerts WHERE event_type = 'health'"))
    op.drop_constraint("ck_alert_event_source", "alerts", type_="check")
    op.drop_constraint("fk_alerts_health_assessment_id", "alerts", type_="foreignkey")
    op.drop_column("alerts", "health_assessment_id")
    op.create_check_constraint(
        "ck_alert_event_source",
        "alerts",
        "(event_type = 'anomaly' AND fault_classification_id IS NULL) OR "
        "(event_type = 'fault' AND fault_classification_id IS NOT NULL "
        "AND fault_classification_id = source_reading_id)",
    )
