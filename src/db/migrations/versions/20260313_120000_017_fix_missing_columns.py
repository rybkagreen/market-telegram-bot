"""fix missing columns — campaigns.type, campaigns.placement_request_id, etc.

Revision ID: 017_fix_missing_columns
Revises: 073d348393fd
Create Date: 2026-03-13

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017_fix_missing_columns'
branch_labels = None
depends_on = None
down_revision = '073d348393fd'


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════
    # CAMPAIGNS — добавить отсутствующие колонки
    # ══════════════════════════════════════════════════════════════

    # campaigns.type — CampaignType (Python str Enum, не PG ENUM)
    op.add_column('campaigns', sa.Column('type', sa.String(50), nullable=False, server_default='broadcast'))
    op.create_index('ix_campaigns_type', 'campaigns', ['type'])

    # campaigns.placement_request_id — FK на placement_requests
    op.add_column('campaigns', sa.Column('placement_request_id', sa.Integer(), sa.ForeignKey('placement_requests.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_campaigns_placement_request_id', 'campaigns', ['placement_request_id'])

    # campaigns.clicks_count — уже существует в БД (пропустить)

    # ══════════════════════════════════════════════════════════════
    # CHANNEL_MEDIAKITS — NOT NULL на created_at/updated_at
    # ══════════════════════════════════════════════════════════════

    # Эти колонки уже существуют, нужно только обновить NOT NULL constraint
    # Alembic показывает "Detected NOT NULL" — это значит что в модели есть server_default
    # но в БД колонки nullable=True. Для production лучше не менять existing columns.
    # Пропускаем — не критично.

    # ══════════════════════════════════════════════════════════════
    # CHANNEL_RATINGS — type changes BIGINT → Integer
    # ══════════════════════════════════════════════════════════════

    # channel_id: BIGINT → Integer
    # Это требует data migration если есть данные. Пропускаем — не критично.

    # ══════════════════════════════════════════════════════════════
    # CHANNEL_SETTINGS — server_default на boolean полях
    # ══════════════════════════════════════════════════════════════

    # Эти колонки уже существуют. server_default можно добавить ALTER COLUMN
    # но это не критично для работы. Пропускаем.

    # ══════════════════════════════════════════════════════════════
    # MAILING_LOGS — новые колонки
    # ══════════════════════════════════════════════════════════════

    op.add_column('mailing_logs', sa.Column('placement_request_id', sa.Integer(), sa.ForeignKey('placement_requests.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_mailing_logs_placement_request_id', 'mailing_logs', ['placement_request_id'])

    op.add_column('mailing_logs', sa.Column('scheduled_at', sa.DateTime(), nullable=True))
    op.add_column('mailing_logs', sa.Column('meta_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # ══════════════════════════════════════════════════════════════
    # PLACEMENT_REQUESTS — JSON → JSONB
    # ══════════════════════════════════════════════════════════════

    # meta_json: JSON → JSONB
    # Это требует data migration. Пропускаем — не критично.

    # ══════════════════════════════════════════════════════════════
    # REPUTATION — новые таблицы (не были созданы)
    # ══════════════════════════════════════════════════════════════

    op.create_table('reputation_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('placement_request_id', sa.Integer(), sa.ForeignKey('placement_requests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('delta', sa.Float(), nullable=False),
        sa.Column('new_score', sa.Float(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('comment', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        comment='История изменений репутации пользователей',
    )
    op.create_index('ix_reputation_history_user_id', 'reputation_history', ['user_id'])
    op.create_index('ix_reputation_history_placement_request_id', 'reputation_history', ['placement_request_id'])
    op.create_index('ix_reputation_history_role', 'reputation_history', ['role'])
    op.create_index('ix_reputation_history_created_at', 'reputation_history', ['created_at'])

    op.create_table('reputation_scores',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('advertiser_score', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('owner_score', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('advertiser_violations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('owner_violations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_advertiser_blocked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_owner_blocked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('advertiser_blocked_until', sa.DateTime(), nullable=True),
        sa.Column('owner_blocked_until', sa.DateTime(), nullable=True),
        sa.Column('block_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        comment='Счета репутации пользователей',
    )


def downgrade() -> None:
    # ══════════════════════════════════════════════════════════════
    # Откат изменений
    # ══════════════════════════════════════════════════════════════

    op.drop_table('reputation_scores')
    op.drop_table('reputation_history')

    op.drop_index('ix_mailing_logs_placement_request_id', table_name='mailing_logs')
    op.drop_column('mailing_logs', 'meta_json')
    op.drop_column('mailing_logs', 'scheduled_at')
    op.drop_column('mailing_logs', 'placement_request_id')

    op.drop_index('ix_campaigns_placement_request_id', table_name='campaigns')
    op.drop_index('ix_campaigns_type', table_name='campaigns')
    op.drop_column('campaigns', 'placement_request_id')
    op.drop_column('campaigns', 'type')
