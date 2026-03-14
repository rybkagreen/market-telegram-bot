"""merge_008_and_0014

Revision ID: 74ca23ceb6d4
Revises: 008, 0014
Create Date: 2026-03-11 12:24:49.456422+00:00

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "74ca23ceb6d4"
down_revision: str | None = ("008", "0014")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
