"""add test mode flags

Revision ID: 400a42ff6da0
Revises: 6a62b060752f
Create Date: 2026-03-19 12:38:16.996086

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


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


def downgrade() -> None:
    # Remove from placement_requests
    op.drop_index(op.f('ix_placement_requests_is_test'), table_name='placement_requests')
    op.drop_column('placement_requests', 'test_label')
    op.drop_column('placement_requests', 'is_test')
    
    # Remove from telegram_chats
    op.drop_index(op.f('ix_telegram_chats_is_test'), table_name='telegram_chats')
    op.drop_column('telegram_chats', 'is_test')
