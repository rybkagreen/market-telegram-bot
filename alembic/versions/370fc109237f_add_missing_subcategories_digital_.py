"""add_missing_subcategory_medicine

Revision ID: 370fc109237f
Revises: d2c8d8998715
Create Date: 2026-03-10

"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "370fc109237f"
down_revision: str | None = "d2c8d8998715"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Добавить missing подкатегорию medicine."""
    
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
                "topic": "здоровье",
                "subcategory": "medicine",
                "display_name_ru": "Медицина и здоровье",
                "is_active": True,
                "sort_order": 6,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ],
    )


def downgrade() -> None:
    """Удалить добавленную подкатегорию."""
    
    op.execute("""
        DELETE FROM topic_categories 
        WHERE topic = 'здоровье' AND subcategory = 'medicine'
    """)
