"""Store anomaly detection results on sensor readings."""

from alembic import op
import sqlalchemy as sa


revision = "0f87e4a902b1"
down_revision = "4cf64549159c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sensor_readings",
        sa.Column(
            "detection_status",
            sa.String(length=20),
            nullable=False,
            server_default="not_evaluated",
        ),
    )
    op.add_column(
        "sensor_readings",
        sa.Column("anomaly_type", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "sensor_readings",
        sa.Column("detection_message", sa.String(length=255), nullable=True),
    )
    op.create_check_constraint(
        "ck_sensor_reading_detection_status",
        "sensor_readings",
        "detection_status IN ('normal', 'anomaly', 'not_evaluated')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sensor_reading_detection_status",
        "sensor_readings",
        type_="check",
    )
    op.drop_column("sensor_readings", "detection_message")
    op.drop_column("sensor_readings", "anomaly_type")
    op.drop_column("sensor_readings", "detection_status")
