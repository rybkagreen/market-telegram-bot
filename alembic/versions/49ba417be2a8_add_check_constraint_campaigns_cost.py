"""add_check_constraint_campaigns_cost

Revision ID: 49ba417be2a8
Revises: d58411813eee
Create Date: 2026-03-10

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "49ba417be2a8"
down_revision: str | None = "d58411813eee"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_campaigns_cost_positive",
        "campaigns",
        "cost >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_campaigns_cost_positive", "campaigns", type_="check")
