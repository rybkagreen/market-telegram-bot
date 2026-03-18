"""add user_feedback table

Revision ID: 6a62b060752f
Revises: a86e3ba47c30
Create Date: 2026-03-18 11:24:41.023753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a62b060752f'
down_revision: Union[str, None] = 'a86e3ba47c30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type
    sa.Enum('new', 'in_progress', 'resolved', 'rejected', name='feedbackstatus').create(op.get_bind())
    
    op.create_table('user_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('new', 'in_progress', 'resolved', 'rejected', name='feedbackstatus'), nullable=False),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('responded_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['responded_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_user_feedback_user_id'), 'user_feedback', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_feedback_status'), 'user_feedback', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_feedback_status'), table_name='user_feedback')
    op.drop_index(op.f('ix_user_feedback_user_id'), table_name='user_feedback')
    op.drop_table('user_feedback')
    
    # Drop enum type
    sa.Enum('new', 'in_progress', 'resolved', 'rejected', name='feedbackstatus').drop(op.get_bind())
