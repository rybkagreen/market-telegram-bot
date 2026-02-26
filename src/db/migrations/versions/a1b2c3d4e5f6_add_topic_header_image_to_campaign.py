"""Add topic, header, image_file_id to Campaign

Revision ID: a1b2c3d4e5f6
Revises: 9a7b3c4d5e6f
Create Date: 2026-02-26 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '9a7b3c4d5e6f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Добавить поля topic, header, image_file_id в таблицу campaigns."""
    # Добавляем поле topic
    op.add_column('campaigns', sa.Column('topic', sa.String(length=100), nullable=True))

    # Добавляем поле header
    op.add_column('campaigns', sa.Column('header', sa.String(length=255), nullable=True))

    # Добавляем поле image_file_id
    op.add_column('campaigns', sa.Column('image_file_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Удалить поля topic, header, image_file_id из таблицы campaigns."""
    op.drop_column('campaigns', 'image_file_id')
    op.drop_column('campaigns', 'header')
    op.drop_column('campaigns', 'topic')
