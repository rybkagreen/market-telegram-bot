"""add_document_links

Revision ID: s26e001_add_document_links
Revises: s26d002_storno_expense
Create Date: 2026-04-03 23:30:00.000000

Additive migration for document cross-linking (Act, Invoice, Transaction). SAFE FOR PROD.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s26e001_add_document_links"
down_revision: str | None = "s26d002_storno_expense"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Act → Contract ─────────────────────────────────────────
    op.add_column(
        "acts",
        sa.Column("contract_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_acts_contract_id", "acts", ["contract_id"], unique=False)
    op.create_foreign_key(
        "fk_acts_contract_id_contracts",
        "acts",
        "contracts",
        ["contract_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ─── Invoice → PlacementRequest, Contract ───────────────────
    op.add_column(
        "invoices",
        sa.Column("placement_request_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_invoices_placement_request_id",
        "invoices",
        ["placement_request_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_invoices_placement_request_id_placement_requests",
        "invoices",
        "placement_requests",
        ["placement_request_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "invoices",
        sa.Column("contract_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_invoices_contract_id", "invoices", ["contract_id"], unique=False)
    op.create_foreign_key(
        "fk_invoices_contract_id_contracts",
        "invoices",
        "contracts",
        ["contract_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ─── Transaction → Act, Invoice ─────────────────────────────
    op.add_column(
        "transactions",
        sa.Column("act_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_txn_act_id", "transactions", ["act_id"], unique=False)
    op.create_foreign_key(
        "fk_txn_act_id_acts",
        "transactions",
        "acts",
        ["act_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "transactions",
        sa.Column("invoice_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_txn_invoice_id", "transactions", ["invoice_id"], unique=False)
    op.create_foreign_key(
        "fk_txn_invoice_id_invoices",
        "transactions",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # ─── Transaction → Act, Invoice (reverse) ───────────────────
    op.drop_constraint("fk_txn_invoice_id_invoices", "transactions", type_="foreignkey")
    op.drop_index("ix_txn_invoice_id", table_name="transactions")
    op.drop_column("transactions", "invoice_id")

    op.drop_constraint("fk_txn_act_id_acts", "transactions", type_="foreignkey")
    op.drop_index("ix_txn_act_id", table_name="transactions")
    op.drop_column("transactions", "act_id")

    # ─── Invoice → Contract (reverse) ───────────────────────────
    op.drop_constraint("fk_invoices_contract_id_contracts", "invoices", type_="foreignkey")
    op.drop_index("ix_invoices_contract_id", table_name="invoices")
    op.drop_column("invoices", "contract_id")

    # ─── Invoice → PlacementRequest (reverse) ───────────────────
    op.drop_constraint(
        "fk_invoices_placement_request_id_placement_requests",
        "invoices",
        type_="foreignkey",
    )
    op.drop_index("ix_invoices_placement_request_id", table_name="invoices")
    op.drop_column("invoices", "placement_request_id")

    # ─── Act → Contract (reverse) ───────────────────────────────
    op.drop_constraint("fk_acts_contract_id_contracts", "acts", type_="foreignkey")
    op.drop_index("ix_acts_contract_id", table_name="acts")
    op.drop_column("acts", "contract_id")
