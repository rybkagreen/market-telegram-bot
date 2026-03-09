"""add topic categories table

Revision ID: 20260308_141004
Revises: previous_revision
Create Date: 2026-03-08 14:10:04.000000

"""

from collections.abc import Sequence
from datetime import UTC

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260308_141004"
down_revision: str | None = None  # Will be set by Alembic
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create topic_categories table and populate with data."""
    from datetime import datetime

    # Create table
    op.create_table(
        "topic_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=False),
        sa.Column("display_name_ru", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic", "subcategory", name="uq_topic_subcategory"),
        comment="Категории и подкатегории Telegram каналов",
    )

    # Create indexes
    op.create_index("ix_topic_categories_topic", "topic_categories", ["topic"])
    op.create_index("ix_topic_categories_subcategory", "topic_categories", ["subcategory"])
    op.create_index("ix_topic_categories_is_active", "topic_categories", ["is_active"])

    # Populate with data from categories.py
    from src.utils.categories import SUBCATEGORIES

    categories_data = []
    sort_order = 0
    now = datetime.now(UTC)

    for topic, subcats in SUBCATEGORIES.items():
        for subcat, display_name in subcats.items():
            categories_data.append(
                {
                    "topic": topic,
                    "subcategory": subcat,
                    "display_name_ru": display_name,
                    "is_active": True,
                    "sort_order": sort_order,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            sort_order += 1

    # Bulk insert
    op.bulk_insert(
        sa.table(
            "topic_categories",
            sa.column("topic", sa.String()),
            sa.column("subcategory", sa.String()),
            sa.column("display_name_ru", sa.String()),
            sa.column("is_active", sa.Boolean()),
            sa.column("sort_order", sa.Integer()),
            sa.column("created_at", sa.DateTime()),
            sa.column("updated_at", sa.DateTime()),
        ),
        categories_data,
    )


def downgrade() -> None:
    """Drop topic_categories table."""
    op.drop_index("ix_topic_categories_is_active", table_name="topic_categories")
    op.drop_index("ix_topic_categories_subcategory", table_name="topic_categories")
    op.drop_index("ix_topic_categories_topic", table_name="topic_categories")
    op.drop_table("topic_categories")
