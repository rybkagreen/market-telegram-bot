"""ooo_usn_15_support

Revision ID: s26d001_ooo_usn_15_support
Revises: s26c001_vat_invoice_calendar
Create Date: 2026-04-03 22:00:00.000000

Additive migration for ООО УСН 15% expense tracking & min-tax logic. SAFE FOR PROD.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s26d001_ooo_usn_15_support"
down_revision: str | None = "s26c001_vat_invoice_calendar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── KudirRecord: expense tracking fields ─────────────────────
    op.add_column(
        "kudir_records",
        sa.Column(
            "operation_type",
            sa.String(10),
            nullable=False,
            server_default="income",
        ),
    )
    op.add_column(
        "kudir_records",
        sa.Column("expense_category", sa.String(30), nullable=True),
    )
    op.add_column(
        "kudir_records",
        sa.Column("expense_amount", sa.Numeric(12, 2), nullable=True),
    )
    op.create_index(
        "ix_kudir_records_operation_type",
        "kudir_records",
        ["operation_type"],
        unique=False,
    )

    # ─── PlatformQuarterlyRevenue: USN 15% tax calculation fields ─
    op.add_column(
        "platform_quarterly_revenues",
        sa.Column(
            "total_expenses",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "platform_quarterly_revenues",
        sa.Column(
            "tax_base_15",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "platform_quarterly_revenues",
        sa.Column(
            "calculated_tax_15",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "platform_quarterly_revenues",
        sa.Column(
            "min_tax_1",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "platform_quarterly_revenues",
        sa.Column(
            "tax_due",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "platform_quarterly_revenues",
        sa.Column("applicable_rate", sa.String(5), nullable=True),
    )

    # ─── Transaction: expense classification fields ───────────────
    op.add_column(
        "transactions",
        sa.Column("expense_category", sa.String(30), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "is_tax_deductible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    # Transaction
    op.drop_column("transactions", "is_tax_deductible")
    op.drop_column("transactions", "expense_category")

    # PlatformQuarterlyRevenue
    op.drop_column("platform_quarterly_revenues", "applicable_rate")
    op.drop_column("platform_quarterly_revenues", "tax_due")
    op.drop_column("platform_quarterly_revenues", "min_tax_1")
    op.drop_column("platform_quarterly_revenues", "calculated_tax_15")
    op.drop_column("platform_quarterly_revenues", "tax_base_15")
    op.drop_column("platform_quarterly_revenues", "total_expenses")

    # KudirRecord
    op.drop_index("ix_kudir_records_operation_type", table_name="kudir_records")
    op.drop_column("kudir_records", "expense_amount")
    op.drop_column("kudir_records", "expense_category")
    op.drop_column("kudir_records", "operation_type")
