"""fix_missing_columns

Revision ID: 017_fix_missing_columns
Revises: 073d348393fd
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa

revision = '017_fix_missing_columns'
down_revision = '073d348393fd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('campaigns', sa.Column(
        'type', sa.String(50), nullable=False, server_default='broadcast'
    ))
    op.add_column('campaigns', sa.Column(
        'placement_request_id', sa.Integer(),
        sa.ForeignKey('placement_requests.id', ondelete='SET NULL'),
        nullable=True
    ))
    op.create_index('ix_campaigns_type', 'campaigns', ['type'])


def downgrade() -> None:
    op.drop_index('ix_campaigns_type', table_name='campaigns')
    op.drop_column('campaigns', 'placement_request_id')
    op.drop_column('campaigns', 'type')
