"""
Link Tracking Service — сервис для трекинга кликов по коротким ссылкам.
Спринт 2 — CTR-трекинг для измерения эффективности кампаний.
"""

import logging
import secrets
import string
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class LinkTrackingService:
    """
    Сервис для управления короткими ссылками и трекинга кликов.

    Методы:
        generate_short_link: Создать короткую ссылку
        track_click: Зафиксировать клик
        get_link_stats: Получить статистику по ссылке
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self.short_link_prefix = "/r/"

    def _generate_short_code(self, length: int = 8) -> str:
        """
        Сгенерировать короткий код для ссылки.

        Args:
            length: Длина кода.

        Returns:
            Случайный код из букв и цифр.
        """
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def generate_short_link(
        self,
        campaign_id: int,
        original_url: str,
    ) -> str:
        """
        Создать короткую ссылку для трекинга.

        Args:
            campaign_id: ID кампании.
            original_url: Исходная ссылка рекламодателя.

        Returns:
            Короткая ссылка (например, /r/abc123).
        """
        from sqlalchemy import select

        from src.db.models.campaign import Campaign

        async with async_session_factory() as session:
            # Генерируем уникальный код
            for _ in range(10):  # Максимум 10 попыток
                short_code = self._generate_short_code()

                # Проверяем уникальность
                stmt = select(Campaign).where(Campaign.tracking_short_code == short_code)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    # Находим кампанию и обновляем
                    campaign = await session.get(Campaign, campaign_id)
                    if campaign:
                        campaign.tracking_url = original_url
                        campaign.tracking_short_code = short_code
                        campaign.clicks_count = 0
                        await session.flush()

                        return f"{self.short_link_prefix}{short_code}"

            raise ValueError("Failed to generate unique short code")

    async def track_click(self, short_code: str) -> str | None:
        """
        Зафиксировать клик по короткой ссылке.

        Args:
            short_code: Код ссылки (без префикса).

        Returns:
            Исходная ссылка для редиректа или None если не найдена.
        """
        from datetime import UTC, datetime

        from sqlalchemy import select
        from sqlalchemy import update as sa_update

        from src.db.models.campaign import Campaign
        from src.db.models.click_tracking import ClickTracking

        async with async_session_factory() as session:
            # Находим кампанию по коду
            stmt = select(Campaign).where(Campaign.tracking_short_code == short_code)
            result = await session.execute(stmt)
            campaign = result.scalar_one_or_none()

            if not campaign:
                logger.warning(f"Short link not found: {short_code}")
                return None

            # Инкрементим счётчик кликов
            await session.execute(
                sa_update(Campaign)
                .where(Campaign.id == campaign.id)
                .values(clicks_count=Campaign.clicks_count + 1)
            )

            # Записать в ClickTracking для детальной аналитики
            click = ClickTracking(
                placement_request_id=campaign.id,
                short_code=short_code,
                clicked_at=datetime.now(UTC),
                user_agent=None,  # Can be passed from request if needed
            )
            session.add(click)

            await session.flush()

            logger.info(
                f"Tracked click for campaign {campaign.id}: {campaign.clicks_count + 1} total"
            )

            return campaign.tracking_url

    async def get_link_stats(self, campaign_id: int) -> dict[str, Any]:
        """
        Получить статистику по ссылке кампании.

        Args:
            campaign_id: ID кампании.

        Returns:
            dict с clicks_count, short_link, original_url.
        """
        async with async_session_factory() as session:
            from src.db.models.campaign import Campaign

            campaign = await session.get(Campaign, campaign_id)
            if not campaign:
                return {
                    "clicks_count": 0,
                    "short_link": None,
                    "original_url": None,
                }

            short_link = None
            if campaign.tracking_short_code:
                short_link = f"{self.short_link_prefix}{campaign.tracking_short_code}"

            return {
                "clicks_count": campaign.clicks_count or 0,
                "short_link": short_link,
                "original_url": campaign.tracking_url,
            }


# Глобальный экземпляр
link_tracking_service = LinkTrackingService()
