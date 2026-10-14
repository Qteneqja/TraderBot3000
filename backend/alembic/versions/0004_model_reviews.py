"""Persist reproducible research assessments separately from model artifacts."""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_reviews",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("model_reviews")
