"""add_channel_settings_and_placement_fields

Revision ID: 20260307_180000
Revises: 20260307_170000
Create Date: 2026-03-07 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260307_180000'
down_revision: str | None = 'b377ebf742bf'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Добавить новые поля для настроек канала и размещений."""

    # === TelegramChat: настройки размещения ===
    op.add_column('telegram_chats', sa.Column(
        'max_posts_per_day',
        sa.Integer(),
        nullable=False,
        server_default='2',
        comment='Максимальное количество постов в день'
    ))

    op.add_column('telegram_chats', sa.Column(
        'approval_mode',
        sa.String(20),
        nullable=False,
        server_default='auto',
        comment="Режим одобрения: 'auto' или 'manual'"
    ))

    # === MailingLog: поля для отклонения и автоодобрения ===
    op.add_column('mailing_logs', sa.Column(
        'rejection_reason',
        sa.String(50),
        nullable=True,
        comment='Причина отклонения заявки'
    ))

    op.add_column('mailing_logs', sa.Column(
        'auto_approve_notified',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='Отправлено ли уведомление за 3 часа до автоодобрения'
    ))


def downgrade() -> None:
    """Откатить изменения."""

    # Удаляем поля из MailingLog
    op.drop_column('mailing_logs', 'auto_approve_notified')
    op.drop_column('mailing_logs', 'rejection_reason')

    # Удаляем поля из TelegramChat
    op.drop_column('telegram_chats', 'approval_mode')
    op.drop_column('telegram_chats', 'max_posts_per_day')

    # Примечание: удаление значений из ENUM не поддерживается в PostgreSQL
    # Статус 'changes_requested' останется в базе
