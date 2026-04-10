"""MailingLogRepository for MailingLog model operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from src.db.models.mailing_log import MailingLog
from src.db.repositories.base import BaseRepository


class MailingLogRepository(BaseRepository[MailingLog]):
    """Репозиторий для работы с логами рассылок."""

    model = MailingLog

    async def get_by_mailing(self, mailing_id: int, limit: int = 100) -> list[MailingLog]:
        """Получить логи конкретной рассылки."""
        result = await self.session.execute(
            select(MailingLog)
            .where(MailingLog.mailing_id == mailing_id)
            .order_by(MailingLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(self, user_id: int, limit: int = 50) -> list[MailingLog]:
        """Получить логи рассылок пользователя."""
        result = await self.session.execute(
            select(MailingLog)
            .where(MailingLog.user_id == user_id)
            .order_by(MailingLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_failed_recent(self, hours: int = 24, limit: int = 100) -> list[MailingLog]:
        """Получить недавние ошибки рассылок."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        result = await self.session.execute(
            select(MailingLog)
            .where(
                MailingLog.status == "failed",
                MailingLog.created_at > cutoff,
            )
            .order_by(MailingLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats_for_mailing(self, mailing_id: int) -> dict[str, int]:
        """Получить статистику по рассылке."""
        result = await self.session.execute(
            select(MailingLog.status, func.count())
            .where(MailingLog.mailing_id == mailing_id)
            .group_by(MailingLog.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_sent_today(self) -> int:
        """Получить количество отправленных сегодня."""
        cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count())
            .select_from(MailingLog)
            .where(MailingLog.status == "sent", MailingLog.created_at > cutoff)
        )
        return result.scalar_one() or 0
