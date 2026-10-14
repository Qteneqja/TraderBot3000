"""Persist paper cost assumptions and accrued fees across restarts."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("execution", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("orders", sa.Column("fees_paid", sa.Numeric(24, 10), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("financing_bars", sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("orders") as batch:
        batch.alter_column("execution", server_default=None)
        batch.alter_column("fees_paid", server_default=None)
        batch.alter_column("financing_bars", server_default=None)


def downgrade():
    with op.batch_alter_table("orders") as batch:
        batch.drop_column("financing_bars")
        batch.drop_column("fees_paid")
        batch.drop_column("execution")
