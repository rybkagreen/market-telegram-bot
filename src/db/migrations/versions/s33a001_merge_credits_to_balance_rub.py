"""merge credits into balance_rub, drop credits column

Revision ID: s33a001_merge_credits_to_balance_rub
Revises: t1u2v3w4x5y6_add_language_code_to_users
Create Date: 2026-04-09 00:00:00.000000

Credits field (Integer) is merged into balance_rub (Numeric 12,2).
Since 1 credit = 1 ruble, we add credits to balance_rub then drop the column.
"""

import sqlalchemy as sa
from alembic import op

revision = "s33a001_merge_credits_to_balance_rub"
down_revision = "t1u2v3w4x5y6_add_language_code_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge credits into balance_rub (1 credit = 1 ruble)
    op.execute(
        """
        UPDATE users
        SET balance_rub = balance_rub + CAST(credits AS NUMERIC)
        WHERE credits > 0
        """
    )

    # Drop credits column
    op.drop_column("users", "credits")


def downgrade() -> None:
    # Re-add credits column
    op.add_column(
        "users",
        sa.Column("credits", sa.Integer(), server_default="0", nullable=False),
    )

    # Note: balance_rub values are NOT reverted in downgrade
    # (we can't know which portion came from credits vs direct topups)
