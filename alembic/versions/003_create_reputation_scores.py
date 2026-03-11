"""create reputation scores table

Revision ID: 003
Revises: 002
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reputation_scores',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('advertiser_score', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('owner_score', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('advertiser_violations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('owner_violations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_advertiser_blocked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_owner_blocked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('advertiser_blocked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_blocked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('block_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )


def downgrade() -> None:
    op.drop_table('reputation_scores')
