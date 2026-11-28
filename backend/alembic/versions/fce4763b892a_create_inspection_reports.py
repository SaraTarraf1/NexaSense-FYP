"""Create immutable inspection report snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "fce4763b892a"
down_revision = "45d3fdc829f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inspection_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("equipment_id", sa.Integer(), sa.ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_id", sa.Integer(), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.UniqueConstraint("inspection_id", name="uq_inspection_report_inspection"),
    )
    op.create_index("ix_inspection_reports_owner_created", "inspection_reports", ["user_id", "generated_at", "id"])
    op.create_index("ix_inspection_reports_equipment_id", "inspection_reports", ["equipment_id"])


def downgrade():
    op.drop_table("inspection_reports")
