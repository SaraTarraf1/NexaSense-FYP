"""Store fault classifications for sensor anomalies."""

from alembic import op
import sqlalchemy as sa


revision = "a614ef710b23"
down_revision = "0f87e4a902b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fault_classifications",
        sa.Column("source_reading_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("matches", sa.JSON(), nullable=False),
        sa.Column("missing_sensor_types", sa.JSON(), nullable=False),
        sa.Column(
            "classified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('identified', 'unknown', 'undetermined')",
            name="ck_fault_classification_status",
        ),
        sa.ForeignKeyConstraint(
            ["source_reading_id"], ["sensor_readings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("source_reading_id"),
    )


def downgrade() -> None:
    op.drop_table("fault_classifications")
