"""backfill_channel_settings

Создаёт строку channel_settings (с дефолтными значениями) для всех каналов,
у которых она отсутствует. Это исправляет каналы, добавленные через мини-апп
до патча POST /channels/, который не создавал channel_settings.

Revision ID: e5f6a7b8c9d0
Revises: d1e2f3a4b5c6
Create Date: 2026-03-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        INSERT INTO channel_settings (
            channel_id,
            price_per_post,
            allow_format_post_24h,
            allow_format_post_48h,
            allow_format_post_7d,
            allow_format_pin_24h,
            allow_format_pin_48h,
            max_posts_per_day,
            max_posts_per_week,
            publish_start_time,
            publish_end_time,
            break_start_time,
            break_end_time,
            auto_accept_enabled,
            updated_at
        )
        SELECT
            tc.id,
            1000,
            true,
            true,
            false,
            false,
            false,
            2,
            10,
            '09:00:00',
            '21:00:00',
            NULL,
            NULL,
            false,
            NOW()
        FROM telegram_chats tc
        LEFT JOIN channel_settings cs ON cs.channel_id = tc.id
        WHERE cs.channel_id IS NULL
        """)
    )


def downgrade() -> None:
    # Нет возможности определить, какие строки были созданы этой миграцией —
    # откат не выполняется (допустимо для backfill-миграций).
    pass
