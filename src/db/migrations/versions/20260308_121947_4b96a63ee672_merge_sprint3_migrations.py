"""merge sprint3 migrations

Revision ID: 4b96a63ee672
Revises: 20260307_190000, 20260308_142000
Create Date: 2026-03-08 12:19:47.878113+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b96a63ee672'
down_revision: Union[str, None] = ('20260307_190000', '20260308_142000')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
