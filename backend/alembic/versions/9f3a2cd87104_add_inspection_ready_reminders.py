"""Store scheduled inspection readiness reminders."""

from alembic import op
import sqlalchemy as sa


revision = "9f3a2cd87104"
down_revision = "20a347ba1347"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inspections", sa.Column("ready_reminded_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_inspections_due_reminders",
        "inspections",
        ["status", "ready_reminded_at", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_inspections_due_reminders", table_name="inspections")
    op.drop_column("inspections", "ready_reminded_at")
