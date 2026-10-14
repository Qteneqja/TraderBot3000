"""Immutable outcome attribution and explicit non-promoting research schedules."""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("trade_outcomes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("mode", sa.String(24), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("model_versions.id")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("detail_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("mode", "order_id", name="uq_outcome_mode_order"))
    op.create_index("ix_trade_outcomes_model_id", "trade_outcomes", ["model_id"])
    op.create_index("ix_trade_outcomes_closed_at", "trade_outcomes", ["closed_at"])
    op.create_table("learning_schedules",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("operator", sa.String(120), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("next_due", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_learning_schedules_next_due", "learning_schedules", ["next_due"])
    op.create_table("learning_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("schedule_id", sa.String(64), sa.ForeignKey("learning_schedules.id"), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("worker_id", sa.String(36)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("result", sa.JSON(), nullable=False))
    op.create_index("ix_learning_runs_schedule_id", "learning_runs", ["schedule_id"])
    op.create_index("ix_learning_runs_state", "learning_runs", ["state"])


def downgrade():
    op.drop_table("learning_runs")
    op.drop_table("learning_schedules")
    op.drop_table("trade_outcomes")
