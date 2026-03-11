"""add placement request to mailing log

Revision ID: 005
Revises: 004
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column
    op.add_column('mailing_logs', sa.Column('placement_request_id', sa.Integer(), nullable=True))

    # Create FK
    op.create_foreign_key(
        'fk_mailing_logs_placement_request',
        'mailing_logs', 'placement_requests',
        ['placement_request_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create index
    op.create_index('ix_mailing_logs_placement_request_id', 'mailing_logs', ['placement_request_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_mailing_logs_placement_request_id', table_name='mailing_logs')

    # Drop FK
    op.drop_constraint('fk_mailing_logs_placement_request', 'mailing_logs', type_='foreignkey')

    # Drop column
    op.drop_column('mailing_logs', 'placement_request_id')
