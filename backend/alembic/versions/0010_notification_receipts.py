"""Notification delivery timestamps, retry deadlines and safe failure codes."""

import sqlalchemy as sa

from alembic import op

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    # Legacy times stay unknown rather than inventing historical delivery evidence.
    for name in ('created_at', 'claimed_at', 'delivered_at', 'retry_at'):
        op.add_column('notification_events', sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    op.add_column('notification_events', sa.Column('error_code', sa.String(48), nullable=True))
    op.execute("UPDATE notification_events SET status='UNKNOWN', error_code='INTERRUPTED_DELIVERY' WHERE status='SENDING'")


def downgrade():
    raise RuntimeError('Preserve notification delivery evidence; downgrade is unsupported')
