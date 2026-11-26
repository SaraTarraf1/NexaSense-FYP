"""Allow cancellation of a booking before it starts."""

from alembic import op
import sqlalchemy as sa


revision = "45d3fdc829f1"
down_revision = "9f3a2cd87104"
branch_labels = None
depends_on = None

SCHEDULED_TIMES = (
    "(status = 'scheduled' AND scheduled_at IS NOT NULL "
    "AND started_at IS NULL AND ended_at IS NULL)"
)
STARTED_TIMES = "(status <> 'scheduled' AND started_at IS NOT NULL)"
CANCELLED_TIMES = (
    "(status = 'cancelled' AND scheduled_at IS NOT NULL "
    "AND started_at IS NULL AND ended_at IS NOT NULL)"
)


def upgrade() -> None:
    op.drop_constraint("ck_inspection_execution_times", "inspections", type_="check")
    op.create_check_constraint(
        "ck_inspection_execution_times",
        "inspections",
        f"{SCHEDULED_TIMES} OR {CANCELLED_TIMES} OR {STARTED_TIMES}",
    )
    op.drop_constraint("uq_inspection_schedule_slot", "inspections", type_="unique")
    op.create_index(
        "uq_inspection_schedule_slot",
        "inspections",
        ["equipment_id", "scheduled_at"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled' OR started_at IS NOT NULL"),
    )


def downgrade() -> None:
    # PostgreSQL rejects the downgrade if bookings were cancelled before starting.
    op.drop_constraint("ck_inspection_execution_times", "inspections", type_="check")
    op.create_check_constraint(
        "ck_inspection_execution_times", "inspections", f"{SCHEDULED_TIMES} OR {STARTED_TIMES}"
    )
    op.drop_index("uq_inspection_schedule_slot", table_name="inspections")
    op.create_unique_constraint(
        "uq_inspection_schedule_slot", "inspections", ["equipment_id", "scheduled_at"]
    )
