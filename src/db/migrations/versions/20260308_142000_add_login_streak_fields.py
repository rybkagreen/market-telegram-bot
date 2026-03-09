"""add last_login_at and streak fields to users

Revision ID: 20260308_142000
Revises: 20260308_141004
Create Date: 2026-03-08 14:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260308_142000'
down_revision: str | None = '20260308_141004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add last_login_at, login_streak_days, max_streak_days to users table."""
    op.add_column(
        'users',
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('login_streak_days', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'users',
        sa.Column('max_streak_days', sa.Integer(), nullable=False, server_default='0')
    )

    # Create index for efficient streak queries
    op.create_index('ix_users_last_login_at', 'users', ['last_login_at'])


def downgrade() -> None:
    """Remove last_login_at and streak fields from users table."""
    op.drop_index('ix_users_last_login_at', table_name='users')
    op.drop_column('users', 'max_streak_days')
    op.drop_column('users', 'login_streak_days')
    op.drop_column('users', 'last_login_at')
