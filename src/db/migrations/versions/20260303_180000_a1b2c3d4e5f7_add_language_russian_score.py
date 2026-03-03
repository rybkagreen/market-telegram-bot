"""Add language and russian_score to telegram_chats

Revision ID: a1b2c3d4e5f7
Revises: dfdd56ff6602
Create Date: 2026-03-03 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: str | None = 'dfdd56ff6602'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add language and russian_score columns to telegram_chats."""
    # Add language column with default 'ru'
    op.add_column(
        'telegram_chats',
        sa.Column('language', sa.String(length=10), nullable=False, server_default='ru')
    )

    # Add russian_score column with default 1.0
    op.add_column(
        'telegram_chats',
        sa.Column('russian_score', sa.Float(), nullable=False, server_default='1.0')
    )

    # Create index for filtering by language
    op.create_index('ix_telegram_chats_language', 'telegram_chats', ['language'])

    # Create index for sorting by russian_score
    op.create_index('ix_telegram_chats_russian_score', 'telegram_chats', ['russian_score'])


def downgrade() -> None:
    """Remove language and russian_score columns from telegram_chats."""
    op.drop_index('ix_telegram_chats_russian_score', table_name='telegram_chats')
    op.drop_index('ix_telegram_chats_language', table_name='telegram_chats')
    op.drop_column('telegram_chats', 'russian_score')
    op.drop_column('telegram_chats', 'language')
