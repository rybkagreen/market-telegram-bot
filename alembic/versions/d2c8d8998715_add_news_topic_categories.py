"""add_news_topic_categories

Revision ID: d2c8d8998715
Revises: 25474817ec79
Create Date: 2026-03-10

"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2c8d8998715"
down_revision: str | None = "25474817ec79"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Добавить подкатегории для темы 'новости'."""
    
    op.bulk_insert(
        sa.table(
            "topic_categories",
            sa.column("id", sa.Integer),
            sa.column("topic", sa.String),
            sa.column("subcategory", sa.String),
            sa.column("display_name_ru", sa.String),
            sa.column("is_active", sa.Boolean),
            sa.column("sort_order", sa.Integer),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {
                "topic": "новости",
                "subcategory": "media",
                "display_name_ru": "СМИ и журналистика",
                "is_active": True,
                "sort_order": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "politics",
                "display_name_ru": "Политика",
                "is_active": True,
                "sort_order": 2,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "economy",
                "display_name_ru": "Экономика",
                "is_active": True,
                "sort_order": 3,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "society",
                "display_name_ru": "Общество",
                "is_active": True,
                "sort_order": 4,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "topic": "новости",
                "subcategory": "world",
                "display_name_ru": "Мировые новости",
                "is_active": True,
                "sort_order": 5,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ],
    )


def downgrade() -> None:
    """Удалить подкатегории для темы 'новости'."""
    
    op.execute("""
        DELETE FROM topic_categories 
        WHERE topic = 'новости'
    """)
