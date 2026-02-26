"""Add ai_provider and ai_model to User

Revision ID: 9a7b3c4d5e6f
Revises: 82cd153da6b8
Create Date: 2026-02-26 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9a7b3c4d5e6f'
down_revision: str | None = '82cd153da6b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Добавить поля ai_provider и ai_model в таблицу users."""
    # Добавляем поле ai_provider
    op.add_column('users', sa.Column('ai_provider', sa.String(length=50), nullable=True))

    # Добавляем поле ai_model
    op.add_column('users', sa.Column('ai_model', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Удалить поля ai_provider и ai_model из таблицы users."""
    op.drop_column('users', 'ai_model')
    op.drop_column('users', 'ai_provider')
