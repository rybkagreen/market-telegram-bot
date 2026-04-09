"""add language_code to users

Revision ID: t1u2v3w4x5y6
Revises: s31a001_document_uploads
Create Date: 2026-04-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "t1u2v3w4x5y6"
down_revision: str | None = "s31a001_document_uploads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("language_code", sa.String(10), nullable=True, server_default=None)
    )


def downgrade() -> None:
    op.drop_column("users", "language_code")
