"""Initial schema — consolidated from 36 migrations

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-10

NOTE: This migration was created by consolidating all previous migrations into a
single file. The schema was derived from pg_dump of the live database.

Encrypted columns (inn, kpp, bank_account, etc. in legal_profiles and
platform_account) are stored as plain VARCHAR/TEXT in PostgreSQL.  Encryption is
handled at the ORM level via EncryptedString in
src/core/security/field_encryption.py.

Fix applied: legal_profiles.user_id changed from BigInteger → Integer to match
users.id, eliminating the pre-existing FK type mismatch.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:  # noqa: PLR0915
    # ── Table 1: users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(256), nullable=False),
        sa.Column("last_name", sa.String(256), nullable=True),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("plan", sa.String(16), server_default=sa.text("'free'"), nullable=False),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "balance_rub",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "earned_rub",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("credits", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("referral_code", sa.String(32), nullable=False),
        sa.Column("referred_by_id", sa.Integer(), nullable=True),
        sa.Column("advertiser_xp", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("advertiser_level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("owner_xp", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("owner_level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("ai_uses_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ai_uses_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
        sa.Column(
            "legal_status_completed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("legal_profile_prompted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legal_profile_skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform_rules_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("privacy_policy_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("login_streak_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_streak_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("language_code", sa.String(10), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referral_code", name="users_referral_code_key"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # ── Table 2: badges ───────────────────────────────────────────────────────
    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon_emoji", sa.String(8), nullable=False),
        sa.Column("xp_reward", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("credits_reward", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("condition_type", sa.String(32), nullable=False),
        sa.Column(
            "condition_value",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("is_rare", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.UniqueConstraint("code", name="badges_code_key"),
    )

    # ── Table 3: categories ───────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name_ru", sa.String(128), nullable=False),
        sa.Column(
            "emoji",
            sa.String(8),
            server_default=sa.text("'🔖'"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    # ── Seed categories ──────────────────────────────────────────────
    categories_table = sa.table(
        "categories",
        sa.column("slug", sa.String),
        sa.column("name_ru", sa.String),
        sa.column("emoji", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        categories_table,
        [
            {"slug": "business", "name_ru": "Бизнес", "emoji": "💼", "is_active": True, "sort_order": 1},
            {"slug": "it", "name_ru": "IT и технологии", "emoji": "💻", "is_active": True, "sort_order": 2},
            {"slug": "marketing", "name_ru": "Маркетинг", "emoji": "📢", "is_active": True, "sort_order": 3},
            {"slug": "crypto", "name_ru": "Криптовалюта", "emoji": "₿", "is_active": True, "sort_order": 4},
            {"slug": "psychology", "name_ru": "Психология", "emoji": "🧠", "is_active": True, "sort_order": 5},
            {"slug": "health", "name_ru": "Здоровье", "emoji": "🏥", "is_active": True, "sort_order": 6},
            {"slug": "entertainment", "name_ru": "Развлечения", "emoji": "🎭", "is_active": True, "sort_order": 7},
            {"slug": "travel", "name_ru": "Путешествия", "emoji": "✈️", "is_active": True, "sort_order": 8},
            {"slug": "food", "name_ru": "Еда", "emoji": "🍕", "is_active": True, "sort_order": 9},
            {"slug": "fashion", "name_ru": "Мода и стиль", "emoji": "👗", "is_active": True, "sort_order": 10},
            {"slug": "other", "name_ru": "Другое", "emoji": "🔹", "is_active": True, "sort_order": 11},
        ],
    )

    # ── Table 4: platform_account ─────────────────────────────────────────────
    op.create_table(
        "platform_account",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "escrow_reserved",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "payout_reserved",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "profit_accumulated",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total_topups",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total_payouts",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("legal_name", sa.String(500), nullable=True),
        sa.Column("inn", sa.Text(), nullable=True),
        sa.Column("kpp", sa.String(9), nullable=True),
        sa.Column("ogrn", sa.String(15), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("bank_name", sa.String(200), nullable=True),
        sa.Column("bank_account", sa.Text(), nullable=True),
        sa.Column("bank_bik", sa.String(9), nullable=True),
        sa.Column("bank_corr_account", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Table 5: platform_quarterly_revenues ──────────────────────────────────
    op.create_table(
        "platform_quarterly_revenues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column(
            "usn_revenue",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "vat_accumulated",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "ndfl_withheld",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "total_expenses",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "tax_base_15",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "calculated_tax_15",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "min_tax_1",
            sa.Numeric(14, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("tax_due", sa.Numeric(14, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("applicable_rate", sa.String(5), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "year",
            "quarter",
            name="uq_platform_quarterly_revenues_year_quarter",
        ),
    )

    # ── Table 6: document_counters ────────────────────────────────────────────
    op.create_table(
        "document_counters",
        sa.Column("prefix", sa.String(4), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("current_seq", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("prefix", "year", name="document_counters_pkey"),
    )

    # ── Table 7: kudir_records ────────────────────────────────────────────────
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
        sa.Column(
            "operation_type",
            sa.String(10),
            server_default=sa.text("'income'"),
            nullable=False,
        ),
        sa.Column("expense_category", sa.String(30), nullable=True),
        sa.Column("expense_amount", sa.Numeric(12, 2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Table 8: audit_logs ───────────────────────────────────────────────────
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
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_target_user_id", "audit_logs", ["target_user_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    # ── Table 9: document_uploads ─────────────────────────────────────────────
    op.create_table(
        "document_uploads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("passport_page_group", sa.String(16), nullable=True),
        sa.Column("image_quality_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("quality_issues", sa.Text(), nullable=True),
        sa.Column("is_readable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("extracted_inn", sa.String(20), nullable=True),
        sa.Column("extracted_kpp", sa.String(20), nullable=True),
        sa.Column("extracted_ogrn", sa.String(20), nullable=True),
        sa.Column("extracted_ogrnip", sa.String(20), nullable=True),
        sa.Column("extracted_name", sa.String(500), nullable=True),
        sa.Column(
            "validation_status",
            sa.String(16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("validation_details", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_document_uploads_user_id", "document_uploads", ["user_id"])

    # ── Table 10: telegram_chats ──────────────────────────────────────────────
    op.create_table(
        "telegram_chats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("member_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_er", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("avg_views", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rating", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_parsed_at", sa.DateTime(timezone=False), nullable=True),
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
        sa.Column("is_test", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="telegram_chats_owner_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="telegram_chats_username_key"),
    )
    op.create_index("ix_telegram_chats_category", "telegram_chats", ["category"])
    op.create_index("ix_telegram_chats_is_test", "telegram_chats", ["is_test"])
    op.create_index("ix_telegram_chats_owner_id", "telegram_chats", ["owner_id"])
    op.create_index("ix_telegram_chats_telegram_id", "telegram_chats", ["telegram_id"], unique=True)

    # ── Table 11: channel_settings ────────────────────────────────────────────
    op.create_table(
        "channel_settings",
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column(
            "price_per_post",
            sa.Numeric(10, 2),
            server_default=sa.text("1000"),
            nullable=False,
        ),
        sa.Column(
            "allow_format_post_24h",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_format_post_48h",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_format_post_7d",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "allow_format_pin_24h",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "allow_format_pin_48h",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "max_posts_per_day",
            sa.Integer(),
            server_default=sa.text("2"),
            nullable=False,
        ),
        sa.Column(
            "max_posts_per_week",
            sa.Integer(),
            server_default=sa.text("10"),
            nullable=False,
        ),
        sa.Column("publish_start_time", sa.Time(), nullable=False),
        sa.Column("publish_end_time", sa.Time(), nullable=False),
        sa.Column("break_start_time", sa.Time(), nullable=True),
        sa.Column("break_end_time", sa.Time(), nullable=True),
        sa.Column(
            "auto_accept_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["telegram_chats.id"],
            name="channel_settings_channel_id_fkey",
        ),
        sa.PrimaryKeyConstraint("channel_id"),
    )

    # ── Table 12: channel_mediakits ───────────────────────────────────────────
    op.create_table(
        "channel_mediakits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("audience_description", sa.Text(), nullable=True),
        sa.Column("logo_file_id", sa.String(256), nullable=True),
        sa.Column("theme_color", sa.String(7), nullable=True),
        sa.Column("avg_post_reach", sa.Integer(), nullable=False),
        sa.Column("views_count", sa.Integer(), nullable=False),
        sa.Column("downloads_count", sa.Integer(), nullable=False),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["telegram_chats.id"],
            name="channel_mediakits_channel_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="channel_mediakits_owner_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", name="channel_mediakits_channel_id_key"),
    )

    # ── Table 13: legal_profiles ──────────────────────────────────────────────
    # FIX: user_id is Integer (was bigint in DB), matching users.id type
    op.create_table(
        "legal_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("legal_status", sa.String(30), nullable=False),
        sa.Column("inn", sa.String(300), nullable=True),
        sa.Column("kpp", sa.String(9), nullable=True),
        sa.Column("ogrn", sa.String(15), nullable=True),
        sa.Column("ogrnip", sa.String(15), nullable=True),
        sa.Column("legal_name", sa.String(500), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("tax_regime", sa.String(20), nullable=True),
        sa.Column("bank_name", sa.String(200), nullable=True),
        sa.Column("bank_account", sa.String(300), nullable=True),
        sa.Column("bank_bik", sa.String(9), nullable=True),
        sa.Column("bank_corr_account", sa.String(300), nullable=True),
        sa.Column("yoomoney_wallet", sa.String(300), nullable=True),
        sa.Column("passport_series", sa.String(300), nullable=True),
        sa.Column("passport_number", sa.String(300), nullable=True),
        sa.Column("passport_issued_by", sa.String(1000), nullable=True),
        sa.Column("passport_issue_date", sa.Date(), nullable=True),
        sa.Column("inn_scan_file_id", sa.String(500), nullable=True),
        sa.Column("passport_scan_file_id", sa.String(500), nullable=True),
        sa.Column("self_employed_cert_file_id", sa.String(500), nullable=True),
        sa.Column("company_doc_file_id", sa.String(500), nullable=True),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("inn_hash", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="legal_profiles_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="legal_profiles_user_id_key"),
    )
    op.create_index("ix_legal_profiles_inn_hash", "legal_profiles", ["inn_hash"])
    op.create_index("ix_legal_profiles_user_id", "legal_profiles", ["user_id"], unique=True)

    # ── Table 14: reputation_scores ───────────────────────────────────────────
    op.create_table(
        "reputation_scores",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "advertiser_score",
            sa.Float(),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column("owner_score", sa.Float(), server_default=sa.text("5"), nullable=False),
        sa.Column(
            "is_advertiser_blocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_owner_blocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("advertiser_blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "advertiser_violations_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "owner_violations_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="reputation_scores_user_id_fkey"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # ── Table 15: payout_requests ─────────────────────────────────────────────
    op.create_table(
        "payout_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "paid",
                "rejected",
                "cancelled",
                name="payoutstatus",
            ),
            nullable=False,
        ),
        sa.Column("requisites", sa.String(512), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
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
        sa.Column(
            "ndfl_withheld",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=True,
        ),
        sa.Column("npd_receipt_number", sa.String(64), nullable=True),
        sa.Column("npd_receipt_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "npd_status",
            sa.String(20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], name="payout_requests_admin_id_fkey"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="payout_requests_owner_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payout_requests_owner_id", "payout_requests", ["owner_id"])
    op.create_index("ix_payout_requests_status", "payout_requests", ["status"])

    # ── Table 16: user_badges ─────────────────────────────────────────────────
    op.create_table(
        "user_badges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("badge_type", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.Column("badge_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"], name="fk_user_badges_badge_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="user_badges_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
    op.create_index("ix_user_badges_badge_id", "user_badges", ["badge_id"])

    # ── Table 17: badge_achievements ──────────────────────────────────────────
    op.create_table(
        "badge_achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column("achievement_type", sa.String(64), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["badge_id"], ["badges.id"], name="badge_achievements_badge_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_badge_achievements_badge_id", "badge_achievements", ["badge_id"])

    # ── Table 18: user_feedback ───────────────────────────────────────────────
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            server_default=sa.text("'NEW'"),
            nullable=False,
        ),
        sa.Column("admin_response", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_by_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["responded_by_id"],
            ["users.id"],
            name="user_feedback_responded_by_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="user_feedback_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_feedback_status", "user_feedback", ["status"])
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])

    # ── Table 19: yookassa_payments ───────────────────────────────────────────
    op.create_table(
        "yookassa_payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("payment_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("desired_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("payment_url", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("payment_method_type", sa.String(16), nullable=True),
        sa.Column("receipt_id", sa.String(64), nullable=True),
        sa.Column("yookassa_metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="yookassa_payments_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_yookassa_payments_payment_id",
        "yookassa_payments",
        ["payment_id"],
        unique=True,
    )
    op.create_index("ix_yookassa_payments_user_id", "yookassa_payments", ["user_id"])

    # ── Table 20: transactions (circular FKs added after all tables) ──────────
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "topup",
                "escrow_freeze",
                "escrow_release",
                "platform_fee",
                "refund_full",
                "refund_partial",
                "cancel_penalty",
                "owner_cancel_compensation",
                "payout",
                "payout_fee",
                "credits_buy",
                "failed_permissions_refund",
                "bonus",
                "spend",
                "commission",
                "refund",
                "ndfl_withholding",
                "storno",
                "admin_credit",
                "gamification_bonus",
                name="transactiontype",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=True),
        sa.Column("payout_id", sa.Integer(), nullable=True),
        sa.Column("yookassa_payment_id", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
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
        sa.Column("payment_status", sa.String(32), nullable=True),
        sa.Column("balance_before", sa.Numeric(12, 2), nullable=True),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=True),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("counterparty_legal_status", sa.String(30), nullable=True),
        sa.Column(
            "currency",
            sa.String(3),
            server_default=sa.text("'RUB'"),
            nullable=False,
        ),
        sa.Column(
            "vat_amount",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("expense_category", sa.String(30), nullable=True),
        sa.Column(
            "is_tax_deductible",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("reverses_transaction_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_reversed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("act_id", sa.Integer(), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        # Non-circular FKs added inline
        sa.ForeignKeyConstraint(
            ["payout_id"], ["payout_requests.id"], name="transactions_payout_id_fkey"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="transactions_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transactions_placement_request_id",
        "transactions",
        ["placement_request_id"],
    )
    op.create_index("ix_transactions_type", "transactions", ["type"])
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_act_id", "transactions", ["act_id"])
    op.create_index("ix_transactions_invoice_id", "transactions", ["invoice_id"])

    # ── Table 21: placement_requests (escrow FK added after transactions) ──────
    op.create_table(
        "placement_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("advertiser_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending_owner",
                "counter_offer",
                "pending_payment",
                "escrow",
                "published",
                "completed",
                "failed",
                "failed_permissions",
                "refunded",
                "cancelled",
                "ord_blocked",
                name="placementstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "publication_format",
            sa.Enum(
                "post_24h",
                "post_48h",
                "post_7d",
                "pin_24h",
                "pin_48h",
                name="publicationformat",
            ),
            nullable=False,
        ),
        sa.Column("ad_text", sa.Text(), nullable=False),
        sa.Column("proposed_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("final_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("proposed_schedule", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_schedule", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "counter_offer_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("counter_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("counter_schedule", sa.DateTime(timezone=True), nullable=True),
        sa.Column("counter_comment", sa.Text(), nullable=True),
        sa.Column("advertiser_counter_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("advertiser_counter_schedule", sa.DateTime(timezone=True), nullable=True),
        sa.Column("advertiser_counter_comment", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("scheduled_delete_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_reach", sa.Integer(), nullable=True),
        sa.Column("clicks_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("tracking_short_code", sa.String(16), nullable=True),
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
        sa.Column("is_test", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("test_label", sa.String(64), nullable=True),
        sa.Column("sent_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("click_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "media_type",
            sa.String(10),
            server_default=sa.text("'none'"),
            nullable=False,
            comment="MediaType: none/photo/video",
        ),
        sa.Column("video_file_id", sa.String(200), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("video_thumbnail_file_id", sa.String(200), nullable=True),
        sa.Column("video_duration", sa.Integer(), nullable=True, comment="seconds"),
        sa.Column("erid", sa.String(100), nullable=True, comment="ad marking token from ORD"),
        sa.Column("escrow_transaction_id", sa.Integer(), nullable=True),
        sa.Column("meta_json", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["advertiser_id"],
            ["users.id"],
            name="placement_requests_advertiser_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["telegram_chats.id"],
            name="placement_requests_channel_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="placement_requests_owner_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tracking_short_code",
            name="placement_requests_tracking_short_code_key",
        ),
    )
    op.create_index(
        "ix_placement_requests_advertiser_id",
        "placement_requests",
        ["advertiser_id"],
    )
    op.create_index("ix_placement_requests_channel_id", "placement_requests", ["channel_id"])
    op.create_index(
        "ix_placement_requests_escrow_transaction_id",
        "placement_requests",
        ["escrow_transaction_id"],
    )
    op.create_index("ix_placement_requests_expires_at", "placement_requests", ["expires_at"])
    op.create_index("ix_placement_requests_is_test", "placement_requests", ["is_test"])
    op.create_index("ix_placement_requests_owner_id", "placement_requests", ["owner_id"])
    op.create_index(
        "ix_placement_requests_scheduled_delete_at",
        "placement_requests",
        ["scheduled_delete_at"],
    )
    op.create_index("ix_placement_requests_status", "placement_requests", ["status"])
    op.create_index(
        "ix_placement_requests_status_expires",
        "placement_requests",
        ["status", "expires_at"],
    )

    # ── Table 22: contracts ───────────────────────────────────────────────────
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("contract_type", sa.String(30), nullable=False),
        sa.Column(
            "contract_status",
            sa.String(20),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("placement_request_id", sa.Integer(), nullable=True),
        sa.Column("legal_status_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column(
            "template_version",
            sa.String(20),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
        sa.Column("pdf_file_path", sa.String(500), nullable=True),
        sa.Column("pdf_telegram_file_id", sa.String(200), nullable=True),
        sa.Column("signature_method", sa.String(20), nullable=True),
        sa.Column("signature_ip", sa.String(45), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column(
            "kep_requested",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("kep_request_email", sa.String(254), nullable=True),
        sa.Column("role", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            name="contracts_placement_request_id_fkey",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="contracts_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_contracts_placement_request_id",
        "contracts",
        ["placement_request_id"],
    )
    op.create_index(
        "ix_contracts_type_status",
        "contracts",
        ["contract_type", "contract_status"],
    )
    op.create_index("ix_contracts_user_id", "contracts", ["user_id"])

    # ── Table 23: contract_signatures ─────────────────────────────────────────
    op.create_table(
        "contract_signatures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("legal_status", sa.String(30), nullable=False),
        sa.Column(
            "signed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("signature_method", sa.String(20), nullable=False),
        sa.Column("document_hash", sa.String(64), nullable=False),
        sa.Column(
            "template_version",
            sa.String(20),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name="contract_signatures_contract_id_fkey",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="contract_signatures_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_contract_signatures_contract_id",
        "contract_signatures",
        ["contract_id"],
    )
    op.create_index(
        "ix_contract_signatures_signed_at",
        "contract_signatures",
        ["signed_at"],
    )
    op.create_index("ix_contract_signatures_user_id", "contract_signatures", ["user_id"])

    # ── Table 24: acts ────────────────────────────────────────────────────────
    op.create_table(
        "acts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=False),
        sa.Column("act_number", sa.String(20), nullable=False),
        sa.Column(
            "act_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("pdf_path", sa.String(255), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("meta_json", postgresql.JSONB(), nullable=True),
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
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column(
            "act_type",
            sa.String(10),
            server_default=sa.text("'income'"),
            nullable=False,
        ),
        sa.Column(
            "sign_status",
            sa.String(15),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sign_method", sa.String(20), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent_hash", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            ondelete="SET NULL",
            name="fk_acts_contract_id_contracts",
        ),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            name="acts_placement_request_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acts_act_number", "acts", ["act_number"], unique=True)
    op.create_index("ix_acts_contract_id", "acts", ["contract_id"])
    op.create_index("ix_acts_placement_request_id", "acts", ["placement_request_id"])
    op.create_index("ix_acts_sign_status", "acts", ["sign_status"])

    # ── Table 25: invoices ────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(20), nullable=False),
        sa.Column("amount_rub", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "vat_amount",
            sa.Numeric(12, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("pdf_path", sa.String(255), nullable=False),
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
        sa.Column("placement_request_id", sa.Integer(), nullable=True),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            ondelete="SET NULL",
            name="fk_invoices_contract_id_contracts",
        ),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            ondelete="SET NULL",
            name="fk_invoices_placement_request_id_placement_requests",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_invoices_user_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_contract_id", "invoices", ["contract_id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True)
    op.create_index(
        "ix_invoices_placement_request_id",
        "invoices",
        ["placement_request_id"],
    )
    op.create_index("ix_invoices_user_id", "invoices", ["user_id"])

    # ── Table 26: ord_registrations ───────────────────────────────────────────
    op.create_table(
        "ord_registrations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("advertiser_ord_id", sa.String(100), nullable=True),
        sa.Column("creative_ord_id", sa.String(100), nullable=True),
        sa.Column("erid", sa.String(100), nullable=True),
        sa.Column(
            "ord_provider",
            sa.String(50),
            server_default=sa.text("'default'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("yandex_request_id", sa.String(128), nullable=True),
        sa.Column("platform_ord_id", sa.String(128), nullable=True),
        sa.Column("contract_ord_id", sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name="ord_registrations_contract_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            name="ord_registrations_placement_request_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "placement_request_id",
            name="ord_registrations_placement_request_id_key",
        ),
    )
    op.create_index("ix_ord_registrations_erid", "ord_registrations", ["erid"])
    op.create_index(
        "ix_ord_registrations_placement_request_id",
        "ord_registrations",
        ["placement_request_id"],
        unique=True,
    )

    # ── Table 27: mailing_logs ────────────────────────────────────────────────
    op.create_table(
        "mailing_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=True),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("chat_id", sa.Integer(), nullable=True),
        sa.Column("chat_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("meta_json", postgresql.JSONB(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["telegram_chats.id"],
            ondelete="SET NULL",
            name="mailing_logs_chat_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            ondelete="SET NULL",
            name="mailing_logs_placement_request_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "placement_request_id",
            "chat_id",
            name="uq_mailing_placement_chat",
        ),
    )
    op.create_index("ix_mailing_logs_campaign_id", "mailing_logs", ["campaign_id"])
    op.create_index("ix_mailing_logs_chat_id", "mailing_logs", ["chat_id"])
    op.create_index(
        "ix_mailing_logs_chat_telegram_id",
        "mailing_logs",
        ["chat_telegram_id"],
    )
    op.create_index(
        "ix_mailing_logs_placement_request_id",
        "mailing_logs",
        ["placement_request_id"],
    )
    op.create_index("ix_mailing_logs_status", "mailing_logs", ["status"])
    op.create_index("ix_mailing_sent_at", "mailing_logs", ["sent_at"])
    op.create_index("ix_mailing_status_chat", "mailing_logs", ["status", "chat_id"])

    # ── Table 28: click_tracking ──────────────────────────────────────────────
    op.create_table(
        "click_tracking",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=False),
        sa.Column("short_code", sa.String(16), nullable=False),
        sa.Column(
            "clicked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            ondelete="CASCADE",
            name="click_tracking_placement_request_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_click_tracking_placement_request_id",
        "click_tracking",
        ["placement_request_id"],
    )
    op.create_index("ix_click_tracking_short_code", "click_tracking", ["short_code"])

    # ── Table 29: placement_disputes ──────────────────────────────────────────
    op.create_table(
        "placement_disputes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=False),
        sa.Column("advertiser_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "post_removed_early",
                "bot_kicked",
                "advertiser_complaint",
                "not_published",
                "wrong_time",
                "wrong_text",
                "early_deletion",
                "other",
                name="disputereason",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "owner_explained",
                "resolved",
                "closed",
                name="disputestatus",
            ),
            nullable=False,
        ),
        sa.Column("owner_explanation", sa.Text(), nullable=True),
        sa.Column("advertiser_comment", sa.Text(), nullable=True),
        sa.Column(
            "resolution",
            sa.Enum(
                "owner_fault",
                "advertiser_fault",
                "technical",
                "partial",
                "full_refund",
                "partial_refund",
                "no_refund",
                "warning",
                name="disputeresolution",
            ),
            nullable=True,
        ),
        sa.Column("resolution_comment", sa.Text(), nullable=True),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("advertiser_refund_pct", sa.Float(), nullable=True),
        sa.Column("owner_payout_pct", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["users.id"],
            name="placement_disputes_admin_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["advertiser_id"],
            ["users.id"],
            name="placement_disputes_advertiser_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="placement_disputes_owner_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            name="placement_disputes_placement_request_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_placement_disputes_placement_request_id",
        "placement_disputes",
        ["placement_request_id"],
    )
    op.create_index("ix_placement_disputes_status", "placement_disputes", ["status"])
    op.create_index("ix_placement_disputes_advertiser_id", "placement_disputes", ["advertiser_id"])
    op.create_index("ix_placement_disputes_owner_id", "placement_disputes", ["owner_id"])
    op.create_index("ix_placement_disputes_admin_id", "placement_disputes", ["admin_id"])

    # ── Table 30: publication_logs ────────────────────────────────────────────
    op.create_table(
        "publication_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("placement_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("post_url", sa.String(500), nullable=True),
        sa.Column("erid", sa.String(100), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("extra", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["placement_id"],
            ["placement_requests.id"],
            ondelete="RESTRICT",
            name="publication_logs_placement_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publication_logs_channel_id", "publication_logs", ["channel_id"])
    op.create_index("ix_publication_logs_detected_at", "publication_logs", ["detected_at"])
    op.create_index("ix_publication_logs_event_type", "publication_logs", ["event_type"])
    op.create_index("ix_publication_logs_placement_id", "publication_logs", ["placement_id"])

    # ── Table 31: reviews ─────────────────────────────────────────────────────
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("reviewed_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
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
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            name="reviews_placement_request_id_fkey",
        ),
        sa.ForeignKeyConstraint(["reviewed_id"], ["users.id"], name="reviews_reviewed_id_fkey"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], name="reviews_reviewer_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "placement_request_id",
            "reviewer_id",
            name="uq_review_placement_reviewer",
        ),
    )
    op.create_index("ix_reviews_reviewed_id", "reviews", ["reviewed_id"])
    op.create_index("ix_reviews_reviewer_id", "reviews", ["reviewer_id"])

    # ── Table 32: reputation_history ──────────────────────────────────────────
    op.create_table(
        "reputation_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "publication",
                "review_5star",
                "review_4star",
                "review_3star",
                "review_2star",
                "review_1star",
                "cancel_before_escrow",
                "cancel_after_confirm",
                "cancel_systematic",
                "reject_invalid_1",
                "reject_invalid_2",
                "reject_invalid_3",
                "reject_frequent",
                "dispute_owner_fault",
                "recovery_30days",
                "ban_reset",
                name="reputationaction",
            ),
            nullable=False,
        ),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("score_before", sa.Float(), nullable=False),
        sa.Column("score_after", sa.Float(), nullable=False),
        sa.Column("placement_request_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["placement_request_id"],
            ["placement_requests.id"],
            name="reputation_history_placement_request_id_fkey",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="reputation_history_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reputation_history_user_id", "reputation_history", ["user_id"])
    op.create_index(
        "ix_reputation_history_placement_request_id",
        "reputation_history",
        ["placement_request_id"],
    )

    # ── Deferred FK constraints (circular / self-referential) ─────────────────

    # users self-reference
    op.create_foreign_key(
        "users_referred_by_id_fkey", "users", "users", ["referred_by_id"], ["id"],
        ondelete="SET NULL",
    )

    # transactions → placement_requests
    op.create_foreign_key(
        "transactions_placement_request_id_fkey",
        "transactions",
        "placement_requests",
        ["placement_request_id"],
        ["id"],
    )

    # transactions → contracts
    op.create_foreign_key(
        "fk_transactions_contract_id_contracts",
        "transactions",
        "contracts",
        ["contract_id"],
        ["id"],
    )

    # transactions → acts
    op.create_foreign_key(
        "fk_txn_act_id_acts",
        "transactions",
        "acts",
        ["act_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # transactions → invoices
    op.create_foreign_key(
        "fk_txn_invoice_id_invoices",
        "transactions",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # transactions self-reference (reversal chain)
    op.create_foreign_key(
        "fk_txn_reverses",
        "transactions",
        "transactions",
        ["reverses_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # placement_requests → transactions (escrow freeze link)
    op.create_foreign_key(
        "placement_requests_escrow_transaction_id_fkey",
        "placement_requests",
        "transactions",
        ["escrow_transaction_id"],
        ["id"],
    )


def downgrade() -> None:
    # Drop circular / deferred FKs first
    op.drop_constraint(
        "placement_requests_escrow_transaction_id_fkey",
        "placement_requests",
        type_="foreignkey",
    )
    op.drop_constraint("fk_txn_reverses", "transactions", type_="foreignkey")
    op.drop_constraint("fk_txn_invoice_id_invoices", "transactions", type_="foreignkey")
    op.drop_constraint("fk_txn_act_id_acts", "transactions", type_="foreignkey")
    op.drop_constraint("fk_transactions_contract_id_contracts", "transactions", type_="foreignkey")
    op.drop_constraint("transactions_placement_request_id_fkey", "transactions", type_="foreignkey")
    op.drop_constraint("users_referred_by_id_fkey", "users", type_="foreignkey")

    # Drop tables in reverse dependency order
    op.drop_table("reputation_history")
    op.drop_table("reviews")
    op.drop_table("publication_logs")
    op.drop_table("placement_disputes")
    op.drop_table("click_tracking")
    op.drop_table("mailing_logs")
    op.drop_table("ord_registrations")
    op.drop_table("invoices")
    op.drop_table("acts")
    op.drop_table("contract_signatures")
    op.drop_table("contracts")
    op.drop_table("placement_requests")
    op.drop_table("transactions")
    op.drop_table("yookassa_payments")
    op.drop_table("user_feedback")
    op.drop_table("badge_achievements")
    op.drop_table("user_badges")
    op.drop_table("payout_requests")
    op.drop_table("reputation_scores")
    op.drop_table("legal_profiles")
    op.drop_table("channel_mediakits")
    op.drop_table("channel_settings")
    op.drop_table("telegram_chats")
    op.drop_table("document_uploads")
    op.drop_table("audit_logs")
    op.drop_table("kudir_records")
    op.drop_table("document_counters")
    op.drop_table("platform_quarterly_revenues")
    op.drop_table("platform_account")
    op.drop_table("categories")
    op.drop_table("badges")
    op.drop_table("users")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS reputationaction")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS publicationformat")
    op.execute("DROP TYPE IF EXISTS placementstatus")
    op.execute("DROP TYPE IF EXISTS payoutstatus")
    op.execute("DROP TYPE IF EXISTS disputestatus")
    op.execute("DROP TYPE IF EXISTS disputeresolution")
    op.execute("DROP TYPE IF EXISTS disputereason")
