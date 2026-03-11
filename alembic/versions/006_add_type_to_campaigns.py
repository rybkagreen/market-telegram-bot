"""add type to campaigns

Revision ID: 006
Revises: 005
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM type for CampaignType
    campaign_type = postgresql.ENUM(
        'broadcast',
        'placement',
        name='campaigntype',
        create_type=True
    )
    campaign_type.create(op.get_bind(), checkfirst=True)

    # Add columns
    op.add_column('campaigns', sa.Column('type', sa.String(50), nullable=False, server_default='broadcast'))
    op.add_column('campaigns', sa.Column('placement_request_id', sa.Integer(), nullable=True))

    # Create FK
    op.create_foreign_key(
        'fk_campaigns_placement_request',
        'campaigns', 'placement_requests',
        ['placement_request_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create indexes
    op.create_index('ix_campaigns_type', 'campaigns', ['type'])
    op.create_index('ix_campaigns_placement_request_id', 'campaigns', ['placement_request_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_campaigns_placement_request_id', table_name='campaigns')
    op.drop_index('ix_campaigns_type', table_name='campaigns')

    # Drop FK
    op.drop_constraint('fk_campaigns_placement_request', 'campaigns', type_='foreignkey')

    # Drop columns
    op.drop_column('campaigns', 'placement_request_id')
    op.drop_column('campaigns', 'type')

    # Drop ENUM
    campaign_type = postgresql.ENUM(
        'broadcast',
        'placement',
        name='campaigntype',
    )
    campaign_type.drop(op.get_bind(), checkfirst=True)
