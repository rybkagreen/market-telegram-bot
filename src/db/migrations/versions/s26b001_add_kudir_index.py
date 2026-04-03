"""add_kudir_index

Revision ID: s26b001_add_kudir_index
Revises: s26a003_accounting_tax
Create Date: 2026-04-03 19:00:00.000000

Additive index migration for KUDiR export performance. SAFE FOR PROD.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "s26b001_add_kudir_index"
down_revision: str | None = "s26a003_accounting_tax"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_kudir_records_quarter_entry",
        "kudir_records",
        ["quarter", "entry_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_kudir_records_quarter_entry",
        table_name="kudir_records",
    )
