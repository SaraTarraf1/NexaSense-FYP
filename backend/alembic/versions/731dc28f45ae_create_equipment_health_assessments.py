"""Store equipment health assessment history and evidence."""

from alembic import op
import sqlalchemy as sa


revision = "731dc28f45ae"
down_revision = "c54102be79d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment_health_assessments",
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
            "trigger_reading_id", sa.Integer(),
            sa.ForeignKey("sensor_readings.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("message", sa.String(255), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_reading_ids", sa.JSON(), nullable=False),
        sa.Column("fault_rule_ids", sa.JSON(), nullable=False),
        sa.Column("missing_sensor_types", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('normal', 'warning', 'critical', 'insufficient_data')",
            name="ck_equipment_health_assessment_status",
        ),
        sa.UniqueConstraint("trigger_reading_id", name="uq_equipment_health_assessment_trigger"),
    )
    op.create_index(
        "ix_equipment_health_assessment_history", "equipment_health_assessments",
        ["equipment_id", "assessed_at", "id"],
    )
    op.create_index(
        "ix_equipment_health_assessments_inspection_id", "equipment_health_assessments",
        ["inspection_id"],
    )


def downgrade() -> None:
    op.drop_table("equipment_health_assessments")
