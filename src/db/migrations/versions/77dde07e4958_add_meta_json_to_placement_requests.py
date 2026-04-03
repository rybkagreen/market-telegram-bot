"""add_meta_json_to_placement_requests

Revision ID: 77dde07e4958
Revises: p1q2r3s4t5u6
Create Date: 2026-04-02 13:34:55.087733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '77dde07e4958'
down_revision: Union[str, None] = 'p1q2r3s4t5u6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meta_json column to placement_requests table."""
    op.add_column(
        'placement_requests',
        sa.Column('meta_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Remove meta_json column from placement_requests table."""
    op.drop_column('placement_requests', 'meta_json')
