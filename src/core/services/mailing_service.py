"""
Mailing Service для управления рассылками.
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.log_repo import LogData, MailingLogRepository
from src.utils.content_filter.filter import check as content_filter_check

logger = logging.getLogger(__name__)


@dataclass
class CampaignResult:
    """Результат кампании."""

    campaign_id: int
    total_chats: int
    sent_count: int
    failed_count: int
    skipped_count: int
    success_rate: float
    total_cost: float


class MailingService:
    """
    Сервис для управления рассылками.

    Методы:
        run_campaign: Запустить кампанию.
        select_chats: Выбрать чаты для кампании.
        check_rate_limit: Проверить rate limit.
    """

    def __init__(
        self,
        campaign_repo: CampaignRepository,
        log_repo: MailingLogRepository,
    ) -> None:
        """
        Инициализация сервиса.

        Args:
            campaign_repo: Репозиторий кампаний.
            log_repo: Репозиторий логов.
        """
        self.campaign_repo = campaign_repo
        self.log_repo = log_repo

    async def run_campaign(self, campaign_id: int) -> dict[str, Any]:
        """
        Запустить рекламную кампанию.

        Args:
            campaign_id: ID кампании.

        Returns:
            Статистика кампании.
        """
        from src.db.models.campaign import CampaignStatus
        from src.db.models.mailing_log import MailingStatus

        # Получаем кампанию
        campaign = await self.campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Проверяем статус
        if campaign.status not in (
            CampaignStatus.QUEUED,
            CampaignStatus.RUNNING,
        ):
            raise ValueError(f"Campaign {campaign_id} cannot be started")

        # Обновляем статус на running
        await self.campaign_repo.update_status(campaign_id, CampaignStatus.RUNNING)

        # Выбираем чаты
        chats = await self.select_chats(campaign)

        if not chats:
            logger.warning(f"No chats found for campaign {campaign_id}")
            await self.campaign_repo.update_statistics(
                campaign_id, total_chats=0, sent_count=0, failed_count=0, skipped_count=0
            )
            await self.campaign_repo.update_status(campaign_id, CampaignStatus.DONE)
            return {
                "campaign_id": campaign_id,
                "total_chats": 0,
                "sent_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
            }

        # Обновляем общее количество чатов
        await self.campaign_repo.update_statistics(
            campaign_id, total_chats=len(chats)
        )

        # Отправляем сообщения
        sent_count = 0
        failed_count = 0
        skipped_count = 0
        logs_data: list[LogData] = []

        for chat in chats:
            # Проверяем rate limit
            if not await self.check_rate_limit(chat.telegram_id):
                skipped_count += 1
                logs_data.append(
                    LogData(
                        campaign_id=campaign_id,
                        chat_id=chat.id,
                        chat_telegram_id=chat.telegram_id,
                        status=MailingStatus.SKIPPED,
                        error_msg="Rate limit exceeded",
                    )
                )
                continue

            # Проверяем контент
            filter_result = content_filter_check(campaign.text)
            if not filter_result.passed:
                skipped_count += 1
                logs_data.append(
                    LogData(
                        campaign_id=campaign_id,
                        chat_id=chat.id,
                        chat_telegram_id=chat.telegram_id,
                        status=MailingStatus.SKIPPED,
                        error_msg=f"Content filter blocked: {filter_result.categories}",
                    )
                )
                continue

            # Отправляем сообщение (заглушка)
            try:
                # Здесь будет вызов sender.send_message()
                sent_count += 1
                logs_data.append(
                    LogData(
                        campaign_id=campaign_id,
                        chat_id=chat.id,
                        chat_telegram_id=chat.telegram_id,
                        status=MailingStatus.SENT,
                    )
                )
            except Exception as e:
                failed_count += 1
                logs_data.append(
                    LogData(
                        campaign_id=campaign_id,
                        chat_id=chat.id,
                        chat_telegram_id=chat.telegram_id,
                        status=MailingStatus.FAILED,
                        error_msg=str(e),
                    )
                )

            # Пакетная вставка логов каждые 20 отправок
            if len(logs_data) >= 20:
                await self.log_repo.bulk_insert(logs_data)
                logs_data = []

        # Вставляем оставшиеся логи
        if logs_data:
            await self.log_repo.bulk_insert(logs_data)

        # Обновляем статистику кампании
        await self.campaign_repo.update_statistics(
            campaign_id,
            sent_count=sent_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
        )

        # Обновляем статус
        await self.campaign_repo.update_status(campaign_id, CampaignStatus.DONE)

        return {
            "campaign_id": campaign_id,
            "total_chats": len(chats),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "success_rate": round(
                (sent_count / len(chats) * 100) if chats else 0, 2
            ),
        }

    async def select_chats(self, campaign) -> list:
        """
        Выбрать чаты для кампании.

        Args:
            campaign: Кампания.

        Returns:
            Список чатов.
        """
        from src.db.repositories.chat_repo import ChatRepository

        async with self.campaign_repo.session.begin_nested():
            chat_repo = ChatRepository(self.campaign_repo.session)

            # Получаем фильтры
            topics = campaign.get_filter_topics()
            min_members = campaign.get_filter_min_members()
            max_members = campaign.get_filter_max_members()
            blacklist = campaign.get_blacklist()

            # Получаем чаты
            chats = await chat_repo.get_active_filtered(
                topics=topics if topics else None,
                min_members=min_members,
                max_members=max_members,
                exclude_ids=blacklist,
                limit=campaign.user.get_chat_limit_per_campaign(),
            )

            return chats

    async def check_rate_limit(
        self,
        chat_telegram_id: int,
        hours: int = 24,
    ) -> bool:
        """
        Проверить rate limit для чата.

        Args:
            chat_telegram_id: Telegram ID чата.
            hours: Период в часах.

        Returns:
            True если можно отправлять.
        """
        import redis.asyncio as redis

        from src.config.settings import settings

        r = redis.from_url(str(settings.redis_url))

        try:
            key = f"mailing:rate_limit:{chat_telegram_id}"
            ttl = hours * 3600

            # Проверяем是否存在
            exists = await r.exists(key)
            if exists:
                return False

            # Устанавливаем ключ
            await r.setex(key, ttl, "1")
            return True

        finally:
            await r.close()
