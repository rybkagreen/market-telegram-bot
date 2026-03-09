"""merge sprint3 migrations

Revision ID: 4b96a63ee672
Revises: 20260307_190000, 20260308_142000
Create Date: 2026-03-08 12:19:47.878113+00:00

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '4b96a63ee672'
down_revision: str | None = ('20260307_190000', '20260308_142000')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
