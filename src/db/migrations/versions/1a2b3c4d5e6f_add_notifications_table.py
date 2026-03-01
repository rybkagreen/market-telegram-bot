"""Add notifications table

Revision ID: 1a2b3c4d5e6f
Revises: a1b2c3d4e5f6
Create Date: 2026-02-26 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Создать таблицу notifications для хранения истории уведомлений."""
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, default=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="История уведомлений пользователей",
    )

    # Создаём индексы для производительности
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index(
        "ix_notifications_notification_type",
        "notifications",
        ["notification_type"],
    )
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_campaign_id", "notifications", ["campaign_id"])
    op.create_index(
        "ix_notifications_transaction_id",
        "notifications",
        ["transaction_id"],
    )
    op.create_index(
        "ix_notifications_created_at",
        "notifications",
        ["created_at"],
    )


def downgrade() -> None:
    """Удалить таблицу notifications."""
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_transaction_id", table_name="notifications")
    op.drop_index("ix_notifications_campaign_id", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
