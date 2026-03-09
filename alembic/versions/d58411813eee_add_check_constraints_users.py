"""add_check_constraints_users

Revision ID: d58411813eee
Revises: 0015
Create Date: 2026-03-09 15:34:21.431870

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d58411813eee"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add check constraints to users table
    op.create_check_constraint("ck_users_credits_positive", "users", "credits >= 0")
    op.create_check_constraint("ck_users_balance_positive", "users", "balance >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_users_credits_positive", "users", type_="check")
    op.drop_constraint("ck_users_balance_positive", "users", type_="check")
