"""create placement requests table

Revision ID: 001
Revises: 9de36b5c6cd5
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = '9de36b5c6cd5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM type for PlacementStatus
    placement_status = postgresql.ENUM(
        'pending_owner',
        'counter_offer',
        'pending_payment',
        'escrow',
        'published',
        'failed',
        'refunded',
        'cancelled',
        name='placementstatus',
        create_type=True
    )
    placement_status.create(op.get_bind(), checkfirst=True)

    # Create table
    op.create_table(
        'placement_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('advertiser_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('proposed_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('final_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('proposed_schedule', sa.DateTime(timezone=True), nullable=True),
        sa.Column('final_schedule', sa.DateTime(timezone=True), nullable=True),
        sa.Column('proposed_frequency', sa.Integer(), nullable=True),
        sa.Column('final_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending_owner'),
        sa.Column('rejection_reason', sa.String(500), nullable=True),
        sa.Column('counter_offer_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_counter_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escrow_transaction_id', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['advertiser_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['telegram_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['escrow_transaction_id'], ['transactions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_placement_requests_advertiser_id', 'placement_requests', ['advertiser_id'])
    op.create_index('ix_placement_requests_channel_id', 'placement_requests', ['channel_id'])
    op.create_index('ix_placement_requests_campaign_id', 'placement_requests', ['campaign_id'])
    op.create_index('ix_placement_requests_status', 'placement_requests', ['status'])
    op.create_index('ix_placement_requests_expires_at', 'placement_requests', ['expires_at'])
    op.create_index('ix_placement_requests_created_at', 'placement_requests', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_placement_requests_created_at', table_name='placement_requests')
    op.drop_index('ix_placement_requests_expires_at', table_name='placement_requests')
    op.drop_index('ix_placement_requests_status', table_name='placement_requests')
    op.drop_index('ix_placement_requests_campaign_id', table_name='placement_requests')
    op.drop_index('ix_placement_requests_channel_id', table_name='placement_requests')
    op.drop_index('ix_placement_requests_advertiser_id', table_name='placement_requests')

    # Drop table
    op.drop_table('placement_requests')

    # Drop ENUM
    placement_status = postgresql.ENUM(
        'pending_owner',
        'counter_offer',
        'pending_payment',
        'escrow',
        'published',
        'failed',
        'refunded',
        'cancelled',
        name='placementstatus',
    )
    placement_status.drop(op.get_bind(), checkfirst=True)
