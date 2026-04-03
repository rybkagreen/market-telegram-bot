"""storno_and_expense_integration

Revision ID: s26d002_storno_expense
Revises: s26d001_ooo_usn_15_support
Create Date: 2026-04-03 23:00:00.000000

Additive migration for storno handling & expense integration. SAFE FOR PROD.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s26d002_storno_expense"
down_revision: str | None = "s26d001_ooo_usn_15_support"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Transaction: storno/reversal fields ────────────────────
    op.add_column(
        "transactions",
        sa.Column("reverses_transaction_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "is_reversed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_foreign_key(
        "fk_txn_reverses",
        "transactions",
        "transactions",
        ["reverses_transaction_id"],
        ["id"],
    )
    op.create_index(
        "ix_txn_reverses_transaction_id",
        "transactions",
        ["reverses_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_txn_reverses_transaction_id", table_name="transactions")
    op.drop_constraint("fk_txn_reverses", "transactions", type_="foreignkey")
    op.drop_column("transactions", "is_reversed")
    op.drop_column("transactions", "reverses_transaction_id")
