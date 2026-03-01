"""add_credits_ai_counter_plan_expiry

Revision ID: 20260301_120000
Revises: 0ea082555ca4
Create Date: 2026-03-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260301_120000"
down_revision: str | None = "0ea082555ca4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Добавить колонки для системы кредитов."""

    # Добавляем колонку credits
    op.add_column("users", sa.Column("credits", sa.Integer(), server_default="0", nullable=False))

    # Добавляем колонку ai_generations_used
    op.add_column(
        "users", sa.Column("ai_generations_used", sa.Integer(), server_default="0", nullable=False)
    )

    # Добавляем колонку plan_expires_at
    op.add_column("users", sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True))

    # Мигрируем данные: balance (Decimal рубли) → credits (int)
    # 1 рубль = 1 кредит
    op.execute("UPDATE users SET credits = FLOOR(balance)::integer")

    # Создаём таблицу crypto_payments
    op.create_table(
        "crypto_payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.Enum("cryptobot", "stars", name="paymentmethod"), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("amount", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("telegram_payment_charge_id", sa.String(length=128), nullable=True),
        sa.Column("stars_amount", sa.Integer(), nullable=True),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("bonus_credits", sa.Integer(), default=0),
        sa.Column(
            "status",
            sa.Enum("pending", "paid", "expired", "cancelled", name="paymentstatus"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("credited_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Создаём индексы для crypto_payments
    op.create_index("ix_crypto_payments_user_id", "crypto_payments", ["user_id"], unique=False)
    op.create_index("ix_crypto_payments_invoice_id", "crypto_payments", ["invoice_id"], unique=True)
    op.create_index("ix_crypto_payments_status", "crypto_payments", ["status"], unique=False)
    op.create_index(
        "ix_crypto_payments_user_status", "crypto_payments", ["user_id", "status"], unique=False
    )
    op.create_index(
        "ix_crypto_payments_credited_at", "crypto_payments", ["credited_at"], unique=False
    )


def downgrade() -> None:
    """Откатить миграцию."""
    # Удаляем таблицу crypto_payments
    op.drop_index("ix_crypto_payments_credited_at", table_name="crypto_payments")
    op.drop_index("ix_crypto_payments_user_status", table_name="crypto_payments")
    op.drop_index("ix_crypto_payments_status", table_name="crypto_payments")
    op.drop_index("ix_crypto_payments_invoice_id", table_name="crypto_payments")
    op.drop_index("ix_crypto_payments_user_id", table_name="crypto_payments")
    op.drop_table("crypto_payments")

    # Удаляем колонки
    op.drop_column("users", "plan_expires_at")
    op.drop_column("users", "ai_generations_used")
    op.drop_column("users", "credits")
