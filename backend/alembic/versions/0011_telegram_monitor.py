"""Durable, recipient-bound read-only monitoring cursor."""

import sqlalchemy as sa

from alembic import op

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('telegram_monitor_cursors',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('next_update', sa.Integer(), nullable=False),
        sa.Column('initialized', sa.Boolean(), nullable=False))


def downgrade():
    raise RuntimeError('Preserve Telegram cursor evidence; downgrade is unsupported')
