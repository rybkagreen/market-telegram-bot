"""create channel settings table

Revision ID: 002
Revises: 001
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'channel_settings',
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('price_per_post', sa.Numeric(10, 2), nullable=False, server_default='500.00'),
        sa.Column('daily_package_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('daily_package_max', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('daily_package_discount', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('weekly_package_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('weekly_package_max', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('weekly_package_discount', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('subscription_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('subscription_min_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('subscription_max_days', sa.Integer(), nullable=False, server_default='365'),
        sa.Column('subscription_max_per_day', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('publish_start_time', sa.Time(), nullable=False, server_default='09:00:00'),
        sa.Column('publish_end_time', sa.Time(), nullable=False, server_default='21:00:00'),
        sa.Column('break_start_time', sa.Time(), nullable=True, server_default='14:00:00'),
        sa.Column('break_end_time', sa.Time(), nullable=True, server_default='15:00:00'),
        sa.Column('auto_accept_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_accept_min_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['telegram_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('channel_id')
    )

    op.create_index('ix_channel_settings_owner_id', 'channel_settings', ['owner_id'])


def downgrade() -> None:
    op.drop_index('ix_channel_settings_owner_id', table_name='channel_settings')
    op.drop_table('channel_settings')
