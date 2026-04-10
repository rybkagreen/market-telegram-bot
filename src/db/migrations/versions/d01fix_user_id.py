"""fix_legal_profiles_user_id_type — BigInteger to Integer

Revision ID: d01fix_user_id
Revises: t1u2v3w4x5y6
Create Date: 2026-04-09
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d01fix_user_id"
down_revision: str | None = "t1u2v3w4x5y6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change legal_profiles.user_id from BIGINT to INTEGER to match users.id."""
    op.alter_column(
        "legal_profiles",
        "user_id",
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="user_id::integer",
    )


def downgrade() -> None:
    """Revert legal_profiles.user_id back to BIGINT."""
    op.alter_column(
        "legal_profiles",
        "user_id",
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="user_id::bigint",
    )
