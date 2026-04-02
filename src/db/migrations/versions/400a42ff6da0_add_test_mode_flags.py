"""add test mode flags and mailing_logs table

Revision ID: 400a42ff6da0
Revises: 6a62b060752f
Create Date: 2026-03-19 12:38:16.996086

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '400a42ff6da0'
down_revision: str | None = '6a62b060752f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_test to telegram_chats
    op.add_column('telegram_chats',
        sa.Column('is_test', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index(op.f('ix_telegram_chats_is_test'), 'telegram_chats', ['is_test'])

    # Add is_test and test_label to placement_requests
    op.add_column('placement_requests',
        sa.Column('is_test', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('placement_requests',
        sa.Column('test_label', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_placement_requests_is_test'), 'placement_requests', ['is_test'])

    # Create mailing_status enum using raw SQL to avoid caching issues
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mailingstatus AS ENUM (
                'pending_approval', 'queued', 'pending', 'sent', 'failed',
                'skipped', 'rejected', 'changes_requested', 'paid'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create mailing_logs table
    op.create_table(
        'mailing_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('placement_request_id', sa.Integer(), sa.ForeignKey('placement_requests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('chat_id', sa.Integer(), sa.ForeignKey('telegram_chats.id', ondelete='SET NULL'), nullable=True),
        sa.Column('chat_telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('message_id', sa.BigInteger(), nullable=True),
        sa.Column('cost', sa.Numeric(12, 2), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_msg', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('meta_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('placement_request_id', 'chat_id', name='uq_mailing_placement_chat'),
    )

    # Create indexes
    op.create_index('ix_mailing_logs_placement_request_id', 'mailing_logs', ['placement_request_id'])
    op.create_index('ix_mailing_logs_campaign_id', 'mailing_logs', ['campaign_id'])
    op.create_index('ix_mailing_logs_chat_id', 'mailing_logs', ['chat_id'])
    op.create_index('ix_mailing_logs_chat_telegram_id', 'mailing_logs', ['chat_telegram_id'])
    op.create_index('ix_mailing_logs_status', 'mailing_logs', ['status'])
    op.create_index('ix_mailing_logs_status_chat', 'mailing_logs', ['status', 'chat_id'])
    op.create_index('ix_mailing_logs_sent_at', 'mailing_logs', ['sent_at'])

    # Create click_tracking table
    op.create_table(
        'click_tracking',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('placement_request_id', sa.Integer(), sa.ForeignKey('placement_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('short_code', sa.String(16), nullable=False),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('user_agent', sa.String(512), nullable=True),
    )

    op.create_index('ix_click_tracking_placement_request_id', 'click_tracking', ['placement_request_id'])
    op.create_index('ix_click_tracking_short_code', 'click_tracking', ['short_code'])


def downgrade() -> None:
    # Remove click_tracking
    op.drop_index('ix_click_tracking_short_code')
    op.drop_index('ix_click_tracking_placement_request_id')
    op.drop_table('click_tracking')

    # Remove mailing_logs
    op.drop_index('ix_mailing_logs_sent_at')
    op.drop_index('ix_mailing_logs_status_chat')
    op.drop_index('ix_mailing_logs_status')
    op.drop_index('ix_mailing_logs_chat_telegram_id')
    op.drop_index('ix_mailing_logs_chat_id')
    op.drop_index('ix_mailing_logs_campaign_id')
    op.drop_index('ix_mailing_logs_placement_request_id')
    op.drop_table('mailing_logs')

    # Remove from placement_requests
    op.drop_index(op.f('ix_placement_requests_is_test'), table_name='placement_requests')
    op.drop_column('placement_requests', 'test_label')
    op.drop_column('placement_requests', 'is_test')

    # Remove from telegram_chats
    op.drop_index(op.f('ix_telegram_chats_is_test'), table_name='telegram_chats')
    op.drop_column('telegram_chats', 'is_test')
