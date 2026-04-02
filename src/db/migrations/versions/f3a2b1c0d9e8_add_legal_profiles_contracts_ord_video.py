"""add_legal_profiles_contracts_ord_video

Revision ID: f3a2b1c0d9e8
Revises: 05dc4bdbdc58
Create Date: 2026-03-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3a2b1c0d9e8"
down_revision: str | None = "0d44c4e12b6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Create table: legal_profiles ---
    op.create_table(
        "legal_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("legal_status", sa.String(30), nullable=False),
        sa.Column("inn", sa.String(12), nullable=True),
        sa.Column("kpp", sa.String(9), nullable=True),
        sa.Column("ogrn", sa.String(15), nullable=True),
        sa.Column("ogrnip", sa.String(15), nullable=True),
        sa.Column("legal_name", sa.String(500), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("tax_regime", sa.String(20), nullable=True),
        sa.Column("bank_name", sa.String(200), nullable=True),
        sa.Column("bank_account", sa.String(20), nullable=True),
        sa.Column("bank_bik", sa.String(9), nullable=True),
        sa.Column("bank_corr_account", sa.String(20), nullable=True),
        sa.Column("yoomoney_wallet", sa.String(50), nullable=True),
        sa.Column("passport_series", sa.String(4), nullable=True),
        sa.Column("passport_number", sa.String(6), nullable=True),
        sa.Column("passport_issued_by", sa.Text(), nullable=True),
        sa.Column("passport_issue_date", sa.Date(), nullable=True),
        sa.Column("inn_scan_file_id", sa.String(200), nullable=True),
        sa.Column("passport_scan_file_id", sa.String(200), nullable=True),
        sa.Column("self_employed_cert_file_id", sa.String(200), nullable=True),
        sa.Column("company_doc_file_id", sa.String(200), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_legal_profiles_user_id", "legal_profiles", ["user_id"], unique=True)
    op.create_index("ix_legal_profiles_inn", "legal_profiles", ["inn"], unique=False)

    # --- Create table: contracts ---
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("contract_type", sa.String(30), nullable=False),
        sa.Column("contract_status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=True),
        sa.Column("legal_status_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("template_version", sa.String(20), server_default="1.0", nullable=False),
        sa.Column("pdf_file_path", sa.String(500), nullable=True),
        sa.Column("pdf_telegram_file_id", sa.String(200), nullable=True),
        sa.Column("signature_method", sa.String(20), nullable=True),
        sa.Column("signature_ip", sa.String(45), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["placement_request_id"], ["placement_requests.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contracts_user_id", "contracts", ["user_id"], unique=False)
    op.create_index("ix_contracts_placement_request_id", "contracts", ["placement_request_id"], unique=False)
    op.create_index("ix_contracts_type_status", "contracts", ["contract_type", "contract_status"], unique=False)

    # --- Create table: ord_registrations ---
    op.create_table(
        "ord_registrations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("advertiser_ord_id", sa.String(100), nullable=True),
        sa.Column("creative_ord_id", sa.String(100), nullable=True),
        sa.Column("erid", sa.String(100), nullable=True),
        sa.Column("ord_provider", sa.String(50), server_default="default", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["placement_request_id"], ["placement_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("placement_request_id"),
    )
    op.create_index(
        "ix_ord_registrations_placement_request_id", "ord_registrations", ["placement_request_id"], unique=True
    )
    op.create_index("ix_ord_registrations_erid", "ord_registrations", ["erid"], unique=False)

    # --- Add columns to users ---
    op.add_column("users", sa.Column("legal_status_completed", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("legal_profile_prompted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("legal_profile_skipped_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("platform_rules_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("privacy_policy_accepted_at", sa.DateTime(timezone=True), nullable=True))

    # --- Add columns to placement_requests ---
    op.add_column(
        "placement_requests",
        sa.Column("media_type", sa.String(10), server_default="none", nullable=False),
    )
    op.add_column("placement_requests", sa.Column("video_file_id", sa.String(200), nullable=True))
    op.add_column("placement_requests", sa.Column("video_url", sa.String(500), nullable=True))
    op.add_column("placement_requests", sa.Column("video_thumbnail_file_id", sa.String(200), nullable=True))
    op.add_column("placement_requests", sa.Column("video_duration", sa.Integer(), nullable=True))
    op.add_column("placement_requests", sa.Column("erid", sa.String(100), nullable=True))


def downgrade() -> None:
    # --- Remove columns from placement_requests ---
    op.drop_column("placement_requests", "erid")
    op.drop_column("placement_requests", "video_duration")
    op.drop_column("placement_requests", "video_thumbnail_file_id")
    op.drop_column("placement_requests", "video_url")
    op.drop_column("placement_requests", "video_file_id")
    op.drop_column("placement_requests", "media_type")

    # --- Remove columns from users ---
    op.drop_column("users", "privacy_policy_accepted_at")
    op.drop_column("users", "platform_rules_accepted_at")
    op.drop_column("users", "legal_profile_skipped_at")
    op.drop_column("users", "legal_profile_prompted_at")
    op.drop_column("users", "legal_status_completed")

    # --- Drop tables (reverse dependency order) ---
    op.drop_index("ix_ord_registrations_erid", table_name="ord_registrations")
    op.drop_index("ix_ord_registrations_placement_request_id", table_name="ord_registrations")
    op.drop_table("ord_registrations")

    op.drop_index("ix_contracts_type_status", table_name="contracts")
    op.drop_index("ix_contracts_placement_request_id", table_name="contracts")
    op.drop_index("ix_contracts_user_id", table_name="contracts")
    op.drop_table("contracts")

    op.drop_index("ix_legal_profiles_inn", table_name="legal_profiles")
    op.drop_index("ix_legal_profiles_user_id", table_name="legal_profiles")
    op.drop_table("legal_profiles")
