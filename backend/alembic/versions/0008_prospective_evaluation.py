"""One-shot predeclared future evaluation; never promotes models."""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("final_evaluations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("parent_id", sa.String(64), sa.ForeignKey("model_versions.id"), nullable=False, unique=True),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("model_versions.id")),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False))


def downgrade():
    raise RuntimeError("Prospective test evidence must not be deleted by downgrade")
