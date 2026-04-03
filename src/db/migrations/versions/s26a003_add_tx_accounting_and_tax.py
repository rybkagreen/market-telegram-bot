"""add_tx_accounting_and_tax

Revision ID: s26a003_accounting_tax
Revises: s26a002_enrich_yk_payout
Create Date: 2026-04-03 18:00:00.000000

Additive migration for accounting links & tax foundation. SAFE FOR PROD.
Adds: contract_id/counterparty_legal_status/currency to transactions,
      platform_quarterly_revenues table, kudir_records table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s26a003_accounting_tax"
down_revision: str | None = "s26a002_enrich_yk_payout"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Transaction enrichment ───────────────────────────────────
    op.add_column(
        "transactions",
        sa.Column("contract_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("counterparty_legal_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
    )
    op.create_foreign_key(
        "fk_transactions_contract_id_contracts",
        "transactions",
        "contracts",
        ["contract_id"],
        ["id"],
    )
    op.create_index("ix_transactions_contract_id", "transactions", ["contract_id"], unique=False)

    # ─── Platform Quarterly Revenue ──────────────────────────────
    op.create_table(
        "platform_quarterly_revenues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("usn_revenue", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("vat_accumulated", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("ndfl_withheld", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "quarter", name="uq_platform_quarterly_revenues_year_quarter"),
    )

    # ─── KUDiR Records ──────────────────────────────────────────
    op.create_table(
        "kudir_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("quarter", sa.String(10), nullable=False),
        sa.Column("entry_number", sa.Integer(), nullable=False),
        sa.Column(
            "operation_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("income_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("kudir_records")
    op.drop_table("platform_quarterly_revenues")
    op.drop_index("ix_transactions_contract_id", table_name="transactions")
    op.drop_constraint("fk_transactions_contract_id_contracts", "transactions", type_="foreignkey")
    op.drop_column("transactions", "currency")
    op.drop_column("transactions", "counterparty_legal_status")
    op.drop_column("transactions", "contract_id")
