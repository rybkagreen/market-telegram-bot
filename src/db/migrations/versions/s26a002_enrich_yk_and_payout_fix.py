"""enrich_yk_and_payout_fix

Revision ID: s26a002_enrich_yk_payout
Revises: s26a001_add_accounting_acts
Create Date: 2026-04-03 17:00:00.000000

Additive migration for YooKassa webhook enrichment. SAFE FOR PROD.
Adds: payment_method_type, receipt_id, yookassa_metadata to yookassa_payments.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "s26a002_enrich_yk_payout"
down_revision: str | None = "s26a001_add_accounting_acts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "yookassa_payments",
        sa.Column("payment_method_type", sa.String(16), nullable=True),
    )
    op.add_column(
        "yookassa_payments",
        sa.Column("receipt_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "yookassa_payments",
        sa.Column("yookassa_metadata", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("yookassa_payments", "yookassa_metadata")
    op.drop_column("yookassa_payments", "receipt_id")
    op.drop_column("yookassa_payments", "payment_method_type")
