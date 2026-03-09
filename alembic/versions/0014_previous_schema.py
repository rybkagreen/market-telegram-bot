"""Previous schema migration (placeholder)

Revision ID: 0014
Revises:
Create Date: 2026-03-01

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Placeholder for previous migrations
    # All tables already exist in the database
    pass


def downgrade() -> None:
    # Placeholder for previous migrations
    pass
