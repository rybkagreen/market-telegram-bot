"""backfill subcategories for existing channels

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Используем SQL для обновления subcategories
    connection = op.get_bind()

    # Получаем все каналы без subcategory
    result = connection.execute(
        sa.text("""
            SELECT id, title, description, topic
            FROM telegram_chats
            WHERE is_active = true
            AND subcategory IS NULL
            AND topic IS NOT NULL
        """)
    )

    # Импортируем функцию классификации
    from src.utils.categories import classify_subcategory

    updated_count = 0

    for row in result:
        channel_id = row[0]
        title = row[1] or ""
        description = row[2] or ""
        topic = row[3] or ""

        # Классифицируем подкатегорию
        subcategory = classify_subcategory(
            title=title,
            description=description,
            topic=topic,
        )

        if subcategory:
            connection.execute(
                sa.text("""
                    UPDATE telegram_chats
                    SET subcategory = :subcategory
                    WHERE id = :id
                """),
                {"subcategory": subcategory, "id": channel_id},
            )
            updated_count += 1

    print(f"Classified {updated_count} channels with subcategories")


def downgrade() -> None:
    # Не делаем downgrade — классификация полезна
    # Но можно очистить subcategory если нужно
    pass
