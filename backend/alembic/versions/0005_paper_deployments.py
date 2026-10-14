"""Audited paper deployment slots and durable wall-clock observations."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "paper_deployments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(24), sa.ForeignKey("account_snapshots.id"), nullable=False),
        sa.Column("scope_key", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("review_id", sa.String(64), sa.ForeignKey("model_reviews.id"), nullable=False),
        sa.Column("previous_id", sa.String(36), sa.ForeignKey("paper_deployments.id")),
        sa.Column("rollback_of", sa.String(36), sa.ForeignKey("paper_deployments.id")),
        sa.Column("operator", sa.String(120), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("contract", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_deployment_slots",
        sa.Column("account_id", sa.String(24), sa.ForeignKey("account_snapshots.id"), primary_key=True),
        sa.Column("scope_key", sa.String(64), primary_key=True),
        sa.Column("deployment_id", sa.String(36), sa.ForeignKey("paper_deployments.id")),
    )
    op.create_table(
        "paper_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(24), sa.ForeignKey("account_snapshots.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("contract", sa.JSON(), nullable=False),
    )
    op.create_table(
        "paper_samples",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("paper_runs.id"), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("worker_id", sa.String(36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("monotonic_ns", sa.Numeric(24, 0), nullable=False),
        sa.Column("healthy", sa.Boolean(), nullable=False),
        sa.Column("observed_seconds", sa.Numeric(24, 6), nullable=False),
        sa.Column("model_observed_seconds", sa.Numeric(24, 6), nullable=False),
        sa.Column("continuity_break", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
    )
    op.create_index("ix_paper_samples_run_id", "paper_samples", ["run_id"])


def downgrade():
    op.drop_table("paper_samples")
    op.drop_table("paper_runs")
    op.drop_table("paper_deployment_slots")
    op.drop_table("paper_deployments")
