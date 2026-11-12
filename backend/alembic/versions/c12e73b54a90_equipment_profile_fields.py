"""Add equipment identifiers, active status and installation date."""
from alembic import op
import sqlalchemy as sa

revision = "c12e73b54a90"
down_revision = "6a22848584f3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("equipment", sa.Column("identifier", sa.String(100), nullable=True))
    op.add_column("equipment", sa.Column("status", sa.String(20), server_default="active", nullable=False))
    op.add_column("equipment", sa.Column("installation_date", sa.Date(), nullable=True))
    # Existing records keep their numeric primary key and receive a readable identifier.
    op.execute("UPDATE equipment SET identifier = 'EQ-' || CAST(id AS VARCHAR)")
    op.alter_column("equipment", "identifier", nullable=False)
    op.create_unique_constraint("uq_equipment_owner_identifier", "equipment", ["user_id", "identifier"])


def downgrade():
    op.drop_constraint("uq_equipment_owner_identifier", "equipment", type_="unique")
    op.drop_column("equipment", "installation_date")
    op.drop_column("equipment", "status")
    op.drop_column("equipment", "identifier")
