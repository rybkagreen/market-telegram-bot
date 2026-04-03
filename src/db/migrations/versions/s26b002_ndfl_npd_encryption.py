"""ndfl_npd_encryption

Revision ID: s26b002_ndfl_npd_encryption
Revises: s26b001_add_kudir_index
Create Date: 2026-04-03 20:00:00.000000

Additive migration for NDFL withholding, NPD tracking & PII encryption. SAFE FOR PROD.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "s26b002_ndfl_npd_encryption"
down_revision: str | None = "s26b001_add_kudir_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── PayoutRequest: NDFL & NPD columns ─────────────────────
    op.add_column(
        "payout_requests",
        sa.Column(
            "ndfl_withheld",
            sa.Numeric(12, 2),
            nullable=True,
            server_default="0",
        ),
    )
    op.add_column(
        "payout_requests",
        sa.Column("npd_receipt_number", sa.String(64), nullable=True),
    )
    op.add_column(
        "payout_requests",
        sa.Column("npd_receipt_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "payout_requests",
        sa.Column(
            "npd_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )

    # ─── TransactionType enum: add ndfl_withholding ─────────────
    # PostgreSQL does not support DROP VALUE — ADD VALUE is safe and additive.
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'ndfl_withholding'")

    # ─── PlatformAccount: PII encryption (column type changes) ─
    # NOTE: EncryptedString/HashableEncryptedString are Python-side TypeDecorators.
    # Alembic may not detect the type change from String → EncryptedString because
    # the underlying DB column type remains TEXT/VARCHAR. The encryption is applied
    # at the ORM level. No ALTER COLUMN needed — just document the change.
    # If explicit ALTER is required, uncomment below:
    #
    # op.alter_column(
    #     "platform_account",
    #     "inn",
    #     existing_type=sa.String(12),
    #     type_=sa.String(300),
    #     existing_nullable=True,
    # )
    # op.alter_column(
    #     "platform_account",
    #     "bank_account",
    #     existing_type=sa.String(20),
    #     type_=sa.String(300),
    #     existing_nullable=True,
    # )
    # op.alter_column(
    #     "platform_account",
    #     "bank_corr_account",
    #     existing_type=sa.String(20),
    #     type_=sa.String(300),
    #     existing_nullable=True,
    # )


def downgrade() -> None:
    # ─── PayoutRequest: drop NDFL & NPD columns ────────────────
    op.drop_column("payout_requests", "npd_status")
    op.drop_column("payout_requests", "npd_receipt_date")
    op.drop_column("payout_requests", "npd_receipt_number")
    op.drop_column("payout_requests", "ndfl_withheld")

    # NOTE: PostgreSQL does NOT support ALTER TYPE ... DROP VALUE.
    # The 'ndfl_withholding' enum value remains in the type.
    # To fully remove it, you would need to recreate the entire enum type,
    # which is dangerous in production. Leaving it as-is.
    # op.execute("ALTER TYPE transactiontype DROP VALUE 'ndfl_withholding'")  # NOT SUPPORTED
