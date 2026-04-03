"""vat_invoice_calendar

Revision ID: s26c001_vat_invoice_calendar
Revises: s26b002_ndfl_npd_encryption
Create Date: 2026-04-03 21:00:00.000000

Additive migration for VAT tracking, B2B invoices & tax calendar. SAFE FOR PROD.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s26c001_vat_invoice_calendar"
down_revision: str | None = "s26b002_ndfl_npd_encryption"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Transaction: VAT amount ────────────────────────────────
    op.add_column(
        "transactions",
        sa.Column(
            "vat_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    # ─── Invoices table ─────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(20), nullable=False),
        sa.Column("amount_rub", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "vat_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("pdf_path", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_invoices_user_id",
        "invoices",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index(
        "ix_invoices_user_id",
        "invoices",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_invoices_invoice_number",
        "invoices",
        ["invoice_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_column("transactions", "vat_amount")
