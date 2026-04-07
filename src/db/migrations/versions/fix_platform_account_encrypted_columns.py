"""fix_platform_account_encrypted_columns

Revision ID: fix_platform_account_enc
Revises: s28a001_add_yandex_ord_fields
Create Date: 2026-04-04 20:00:00.000000

Fixes column types for encrypted fields in platform_account.
The model uses EncryptedString/HashableEncryptedString which produce
much longer strings than the original VARCHAR(12/20) columns allow.
"""

import sqlalchemy as sa
from alembic import op

revision = "fix_platform_account_enc"
down_revision = "s28a001_add_yandex_ord_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # inn uses HashableEncryptedString(300) — encrypted output can be ~400+ chars
    op.alter_column(
        "platform_account",
        "inn",
        type_=sa.Text(),
        existing_type=sa.String(12),
        nullable=True,
    )
    # bank_account and bank_corr_account use EncryptedString(300)
    op.alter_column(
        "platform_account",
        "bank_account",
        type_=sa.Text(),
        existing_type=sa.String(20),
        nullable=True,
    )
    op.alter_column(
        "platform_account",
        "bank_corr_account",
        type_=sa.Text(),
        existing_type=sa.String(20),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "platform_account",
        "bank_corr_account",
        type_=sa.String(20),
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "platform_account",
        "bank_account",
        type_=sa.String(20),
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "platform_account",
        "inn",
        type_=sa.String(12),
        existing_type=sa.Text(),
        nullable=True,
    )
