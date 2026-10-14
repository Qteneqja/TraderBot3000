"""Durable practice reservations and transaction cursors; submission remains gated."""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("practice_accounts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("cursor", sa.String(32), nullable=False),
        sa.Column("synchronized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconciled", sa.Boolean(), nullable=False),
        sa.Column("suspended", sa.Boolean(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("risk", sa.JSON(), nullable=False),
        sa.Column("approval", sa.JSON(), nullable=False))
    op.create_table("practice_orders",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("account_id", sa.String(64), sa.ForeignKey("practice_accounts.id"), nullable=False),
        sa.Column("signal_id", sa.String(64), nullable=False),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column("units", sa.Numeric(24, 10), nullable=False),
        sa.Column("planned_risk", sa.Numeric(24, 10), nullable=False),
        sa.Column("broker_order_id", sa.String(64)),
        sa.Column("trade_id", sa.String(64)),
        sa.Column("entry", sa.Numeric(24, 10)),
        sa.Column("realized_pnl", sa.Numeric(24, 10)),
        sa.Column("fees_paid", sa.Numeric(24, 10), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("exit", sa.Numeric(24, 10)),
        sa.Column("close_reason", sa.String(48)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "signal_id", name="uq_practice_account_signal"),
        sa.UniqueConstraint("account_id", "client_id", name="uq_practice_account_client"))
    op.create_index("ix_practice_orders_account_id", "practice_orders", ["account_id"])
    op.create_index("ix_practice_orders_state", "practice_orders", ["state"])
    op.create_table("practice_transactions",
        sa.Column("account_id", sa.String(64), sa.ForeignKey("practice_accounts.id"), primary_key=True),
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False))


def downgrade():
    op.drop_table("practice_transactions")
    op.drop_table("practice_orders")
    op.drop_table("practice_accounts")
