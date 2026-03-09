"""add_check_constraint_transactions_amount

Revision ID: 8885dc6d508e
Revises: 49ba417be2a8
Create Date: 2026-03-10

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8885dc6d508e"
down_revision: str | None = "49ba417be2a8"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_transactions_amount_positive",
        "transactions",
        "amount > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transactions_amount_positive", "transactions", type_="check")
