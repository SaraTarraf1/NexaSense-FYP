"""Replace legacy EQ-number identifiers with type-based identifiers."""
import re
from alembic import op
import sqlalchemy as sa

revision = "d23f84c65b01"
down_revision = "c12e73b54a90"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, user_id, equipment_type, identifier FROM equipment ORDER BY id")).mappings().all()
    used = {}
    for row in rows:
        used.setdefault(row["user_id"], set()).add(row["identifier"])
    prefixes = {"ac": "AC", "air conditioner": "AC", "air conditioning": "AC", "hvac": "AC", "electrical panel": "EP", "water pump": "WP", "ventilation": "VU", "ventilation unit": "VU", "water heater": "WH", "heat pump": "HP", "generator": "GEN"}
    for row in rows:
        if not re.fullmatch(r"EQ-?\d+", row["identifier"], re.IGNORECASE):
            continue
        normalized = re.sub(r"[^a-z0-9]+", " ", row["equipment_type"].lower()).strip()
        words = normalized.split()
        prefix = prefixes.get(normalized) or (("".join(word[0] for word in words) if len(words) > 1 else normalized[:4]).upper() or "EQ")
        number = 1
        owner_ids = used[row["user_id"]]
        while f"{prefix}{number}" in owner_ids:
            number += 1
        identifier = f"{prefix}{number}"
        connection.execute(sa.text("UPDATE equipment SET identifier = :identifier WHERE id = :id"), {"identifier": identifier, "id": row["id"]})
        owner_ids.add(identifier)


def downgrade():
    # Preserve user-visible identifiers; renaming them back would lose identity history.
    pass
