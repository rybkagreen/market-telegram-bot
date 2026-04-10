"""add_cascade_to_self_referencing_fks — users.referred_by_id, transactions.reverses_transaction_id

Revision ID: d18cascade_selfref
Revises: d01fix_user_id
Create Date: 2026-04-09
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d18cascade_selfref"
down_revision: str | None = "d01fix_user_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ON DELETE SET NULL to self-referencing FKs."""
    # users.referred_by_id — SET NULL so referred users aren't deleted
    op.drop_constraint("users_referred_by_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_referred_by_id_fkey",
        "users",
        "users",
        ["referred_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # transactions.reverses_transaction_id — SET NULL so reversed txns aren't orphaned
    op.drop_constraint(
        "transactions_reverses_transaction_id_fkey", "transactions", type_="foreignkey"
    )
    op.create_foreign_key(
        "transactions_reverses_transaction_id_fkey",
        "transactions",
        "transactions",
        ["reverses_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Revert to original FKs without CASCADE."""
    op.drop_constraint(
        "transactions_reverses_transaction_id_fkey", "transactions", type_="foreignkey"
    )
    op.create_foreign_key(
        "transactions_reverses_transaction_id_fkey",
        "transactions",
        "transactions",
        ["reverses_transaction_id"],
        ["id"],
    )

    op.drop_constraint("users_referred_by_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_referred_by_id_fkey",
        "users",
        "users",
        ["referred_by_id"],
        ["id"],
    )
