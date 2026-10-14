"""Persist shadow predictions independently of execution decisions."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("candidate_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(24), sa.ForeignKey("instruments.symbol"), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quote_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(24), nullable=False),
        sa.Column("prediction", sa.JSON(), nullable=False),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("model_id", "candidate_id", name="uq_prediction_candidate_model"),
    )


def downgrade():
    op.drop_table("model_predictions")
