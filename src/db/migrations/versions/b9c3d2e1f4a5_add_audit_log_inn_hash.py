"""add_audit_log_inn_hash

Revision ID: b9c3d2e1f4a5
Revises: f3a2b1c0d9e8
Create Date: 2026-03-22 12:00:00.000000

S6A: Adds audit_logs table and inn_hash column to legal_profiles.
NOTE: Existing inn/bank_account/passport data is NOT automatically encrypted.
      Run scripts/encrypt_existing_legal_profiles.py ONCE after applying this migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9c3d2e1f4a5"
down_revision: str | None = "f3a2b1c0d9e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── legal_profiles: add inn_hash column ──────────────────────────────────
    op.add_column("legal_profiles", sa.Column("inn_hash", sa.String(64), nullable=True))
    # Drop old plaintext INN index (now meaningless after encryption)
    op.drop_index("ix_legal_profiles_inn", table_name="legal_profiles", if_exists=True)
    op.create_index("ix_legal_profiles_inn_hash", "legal_profiles", ["inn_hash"])

    # ── Widen encrypted columns (Fernet ciphertext is larger than plaintext) ─
    # EncryptedString uses String(300/500/1000). We alter varchar lengths.
    op.alter_column("legal_profiles", "inn", type_=sa.String(300), existing_nullable=True)
    op.alter_column("legal_profiles", "bank_account", type_=sa.String(300), existing_nullable=True)
    op.alter_column("legal_profiles", "bank_corr_account", type_=sa.String(300), existing_nullable=True)
    op.alter_column("legal_profiles", "yoomoney_wallet", type_=sa.String(300), existing_nullable=True)
    op.alter_column("legal_profiles", "passport_series", type_=sa.String(300), existing_nullable=True)
    op.alter_column("legal_profiles", "passport_number", type_=sa.String(300), existing_nullable=True)
    op.alter_column("legal_profiles", "passport_issued_by", type_=sa.String(1000), existing_nullable=True)
    op.alter_column("legal_profiles", "inn_scan_file_id", type_=sa.String(500), existing_nullable=True)
    op.alter_column("legal_profiles", "passport_scan_file_id", type_=sa.String(500), existing_nullable=True)
    op.alter_column(
        "legal_profiles", "self_employed_cert_file_id", type_=sa.String(500), existing_nullable=True
    )
    op.alter_column("legal_profiles", "company_doc_file_id", type_=sa.String(500), existing_nullable=True)

    # ── audit_logs table ─────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("target_user_id", sa.BigInteger(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_target_user_id", "audit_logs", ["target_user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_legal_profiles_inn_hash", table_name="legal_profiles")
    op.drop_column("legal_profiles", "inn_hash")
    op.create_index("ix_legal_profiles_inn", "legal_profiles", ["inn"])

    # Restore original column sizes
    op.alter_column("legal_profiles", "inn", type_=sa.String(12), existing_nullable=True)
    op.alter_column("legal_profiles", "bank_account", type_=sa.String(20), existing_nullable=True)
    op.alter_column("legal_profiles", "bank_corr_account", type_=sa.String(20), existing_nullable=True)
    op.alter_column("legal_profiles", "yoomoney_wallet", type_=sa.String(50), existing_nullable=True)
    op.alter_column("legal_profiles", "passport_series", type_=sa.String(4), existing_nullable=True)
    op.alter_column("legal_profiles", "passport_number", type_=sa.String(6), existing_nullable=True)
    op.alter_column("legal_profiles", "passport_issued_by", type_=sa.Text(), existing_nullable=True)
    op.alter_column("legal_profiles", "inn_scan_file_id", type_=sa.String(200), existing_nullable=True)
    op.alter_column(
        "legal_profiles", "passport_scan_file_id", type_=sa.String(200), existing_nullable=True
    )
    op.alter_column(
        "legal_profiles", "self_employed_cert_file_id", type_=sa.String(200), existing_nullable=True
    )
    op.alter_column(
        "legal_profiles", "company_doc_file_id", type_=sa.String(200), existing_nullable=True
    )
