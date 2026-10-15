"""Durable bounded narrative-only requests, isolated from trading authority."""

import sqlalchemy as sa

from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('narrative_records',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('source_kind', sa.String(32), nullable=False),
        sa.Column('source_id', sa.String(64), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('model', sa.String(120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True)),
        sa.Column('state', sa.String(24), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('snapshot_sha256', sa.String(64), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False))
    op.create_index('ix_narrative_records_attempted_at', 'narrative_records', ['attempted_at'])
    op.create_index('ix_narrative_records_state', 'narrative_records', ['state'])


def downgrade():
    raise RuntimeError('Preserve narrative request/audit evidence; downgrade is unsupported')
