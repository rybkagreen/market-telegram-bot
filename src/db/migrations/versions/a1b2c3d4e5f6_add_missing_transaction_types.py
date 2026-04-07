"""add_missing_transaction_types

Revision ID: a1b2c3d4e5f6
Revises: 77dde07e4958
Create Date: 2026-04-03 06:20:00.000000

Adds bonus, spend, commission, refund values to the transactiontype enum.
These are used in billing_service.py but were missing from the DB enum.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "77dde07e4958"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL requires each ADD VALUE in a separate statement
    # and it cannot run inside a transaction block for some versions,
    # so we use COMMIT/BEGIN workaround via op.execute
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'bonus'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'spend'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'commission'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'refund'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    # Downgrade is a no-op; removing values would require recreating the type.
    pass
