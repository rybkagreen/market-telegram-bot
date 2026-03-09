"""add_advertiser_owner_xp_levels

Revision ID: 20260307_190000
Revises: 20260307_180000
Create Date: 2026-03-07 19:00:00.000000

Разделение геймификации на независимые прогрессии для рекламодателей и владельцев.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260307_190000'
down_revision: str | None = '20260307_180000'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Добавить раздельные XP и уровни для рекламодателей и владельцев."""

    # === Users: раздельные XP и уровни ===
    op.add_column('users', sa.Column(
        'advertiser_xp',
        sa.Integer(),
        nullable=False,
        server_default='0',
        comment='XP рекламодателя (за запуск кампаний)'
    ))

    op.add_column('users', sa.Column(
        'owner_xp',
        sa.Integer(),
        nullable=False,
        server_default='0',
        comment='XP владельца (за публикации в канале)'
    ))

    op.add_column('users', sa.Column(
        'advertiser_level',
        sa.Integer(),
        nullable=False,
        server_default='1',
        comment='Уровень рекламодателя'
    ))

    op.add_column('users', sa.Column(
        'owner_level',
        sa.Integer(),
        nullable=False,
        server_default='1',
        comment='Уровень владельца канала'
    ))

    # === Индексы для быстрой выборки ===
    op.create_index('ix_users_advertiser_level', 'users', ['advertiser_level'])
    op.create_index('ix_users_owner_level', 'users', ['owner_level'])
    op.create_index('ix_users_advertiser_xp', 'users', ['advertiser_xp'])
    op.create_index('ix_users_owner_xp', 'users', ['owner_xp'])


def downgrade() -> None:
    """Откатить изменения."""

    # Удаляем индексы
    op.drop_index('ix_users_owner_xp', table_name='users')
    op.drop_index('ix_users_advertiser_xp', table_name='users')
    op.drop_index('ix_users_owner_level', table_name='users')
    op.drop_index('ix_users_advertiser_level', table_name='users')

    # Удаляем поля
    op.drop_column('users', 'owner_level')
    op.drop_column('users', 'advertiser_level')
    op.drop_column('users', 'owner_xp')
    op.drop_column('users', 'advertiser_xp')
