"""create reputation history table

Revision ID: 004
Revises: 003
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM type for ReputationAction
    reputation_action = postgresql.ENUM(
        'publication',
        'review_5star',
        'review_4star',
        'review_3star',
        'review_2star',
        'review_1star',
        'cancel_before',
        'cancel_after',
        'cancel_systematic',
        'reject_invalid_1',
        'reject_invalid_2',
        'reject_invalid_3',
        'reject_frequent',
        'recovery_30days',
        'ban_reset',
        'initial_migration',
        name='reputationaction',
        create_type=True
    )
    reputation_action.create(op.get_bind(), checkfirst=True)

    # Create table
    op.create_table(
        'reputation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('placement_request_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('delta', sa.Float(), nullable=False),
        sa.Column('new_score', sa.Float(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('comment', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['placement_request_id'], ['placement_requests.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_reputation_history_user_id', 'reputation_history', ['user_id'])
    op.create_index('ix_reputation_history_placement_request_id', 'reputation_history', ['placement_request_id'])
    op.create_index('ix_reputation_history_created_at', 'reputation_history', ['created_at'])
    op.create_index('ix_reputation_history_role', 'reputation_history', ['role'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_reputation_history_role', table_name='reputation_history')
    op.drop_index('ix_reputation_history_created_at', table_name='reputation_history')
    op.drop_index('ix_reputation_history_placement_request_id', table_name='reputation_history')
    op.drop_index('ix_reputation_history_user_id', table_name='reputation_history')

    # Drop table
    op.drop_table('reputation_history')

    # Drop ENUM
    reputation_action = postgresql.ENUM(
        'publication',
        'review_5star',
        'review_4star',
        'review_3star',
        'review_2star',
        'review_1star',
        'cancel_before',
        'cancel_after',
        'cancel_systematic',
        'reject_invalid_1',
        'reject_invalid_2',
        'reject_invalid_3',
        'reject_frequent',
        'recovery_30days',
        'ban_reset',
        'initial_migration',
        name='reputationaction',
    )
    reputation_action.drop(op.get_bind(), checkfirst=True)
