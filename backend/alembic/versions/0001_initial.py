"""Initial schema. The v1 metadata snapshot is frozen in this migration package."""

from alembic import op
from app.database.schema_v1 import metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    metadata.drop_all(op.get_bind())
