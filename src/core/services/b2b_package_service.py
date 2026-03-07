"""
B2B Package Service — сервис для управления пакетными предложениями.
Спринт 3 — B2B-маркетплейс для агентств и крупных рекламодателей.
"""

import logging
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class B2BPackageService:
    """
    Сервис для управления B2B-пакетами.

    Методы:
        get_packages_by_niche: Получить пакеты по нише
        validate_package_channels: Проверить каналы в пакете
        get_package_actual_reach: Получить фактический охват пакета
        calculate_package_discount: Рассчитать скидку пакета
    """

    # Описание ниш для пользователей
    NICHE_DESCRIPTIONS = {
        "it": "💻 IT и технологии — разработчики, стартапы, digital-специалисты",
        "business": "💼 Бизнес — предприниматели, менеджеры, корпоративные клиенты",
        "realestate": "🏠 Недвижимость — застройщики, риелторы, инвесторы",
        "crypto": "🔗 Криптовалюты — трейдеры, инвесторы, блокчейн-энтузиасты",
        "marketing": "📈 Маркетинг — маркетологи, SMM-специалисты, агентства",
        "finance": "💰 Финансы — инвесторы, трейдеры, финансовые консультанты",
    }

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def get_packages_by_niche(
        self,
        niche: str,
    ) -> list[dict[str, Any]]:
        """
        Получить пакеты по нише.

        Args:
            niche: Название ниши (it, business, realestate, crypto, marketing, finance).

        Returns:
            Список активных пакетов.
        """
        from sqlalchemy import select

        from src.db.models.b2b_package import B2BPackage

        async with async_session_factory() as session:
            stmt = (
                select(B2BPackage)
                .where(
                    B2BPackage.niche == niche,
                    B2BPackage.is_active == True,  # noqa: E712
                )
                .order_by(B2BPackage.price.asc())
            )
            result = await session.execute(stmt)
            packages = list(result.scalars().all())

            return [
                {
                    "id": pkg.id,
                    "name": pkg.name,
                    "niche": pkg.niche,
                    "description": pkg.description,
                    "channels_count": pkg.channels_count,
                    "guaranteed_reach": pkg.guaranteed_reach,
                    "min_er": pkg.min_er,
                    "price": float(pkg.price),
                    "discount_pct": pkg.discount_pct,
                    "is_available": pkg.is_available,
                }
                for pkg in packages
            ]

    async def get_all_packages(self) -> dict[str, list[dict[str, Any]]]:
        """
        Получить все пакеты по нишам.

        Returns:
            dict с нишами как ключами и списками пакетов.
        """
        result = {}
        for niche in self.NICHE_DESCRIPTIONS:
            result[niche] = await self.get_packages_by_niche(niche)
        return result

    async def validate_package_channels(
        self,
        package_id: int,
    ) -> dict[str, Any]:
        """
        Проверить каналы в пакете на активность.

        Args:
            package_id: ID пакета.

        Returns:
            dict с valid, active_channels, inactive_channels.
        """

        from src.db.models.analytics import TelegramChat
        from src.db.models.b2b_package import B2BPackage

        async with async_session_factory() as session:
            package = await session.get(B2BPackage, package_id)
            if not package:
                return {"error": "Package not found"}

            channel_ids = package.channel_ids
            active_channels = []
            inactive_channels = []

            for channel_id in channel_ids:
                channel = await session.get(TelegramChat, channel_id)
                if channel and channel.is_active and channel.is_accepting_ads:
                    active_channels.append(channel_id)
                else:
                    inactive_channels.append(channel_id)

            return {
                "package_id": package_id,
                "valid": len(inactive_channels) == 0,
                "active_channels": active_channels,
                "inactive_channels": inactive_channels,
                "total_channels": len(channel_ids),
            }

    async def get_package_actual_reach(
        self,
        package_id: int,
    ) -> dict[str, Any]:
        """
        Получить фактический охват пакета на текущий момент.

        Args:
            package_id: ID пакета.

        Returns:
            dict с actual_reach, guaranteed_reach, difference.
        """
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat
        from src.db.models.b2b_package import B2BPackage

        async with async_session_factory() as session:
            package = await session.get(B2BPackage, package_id)
            if not package:
                return {"error": "Package not found"}

            # Получаем каналы пакета
            stmt = (
                select(TelegramChat)
                .where(
                    TelegramChat.id.in_(package.channel_ids),
                    TelegramChat.is_active == True,  # noqa: E712
                )
            )
            result = await session.execute(stmt)
            channels = list(result.scalars().all())

            # Считаем фактический охват
            actual_reach = sum(ch.last_avg_views or 0 for ch in channels)

            return {
                "package_id": package_id,
                "actual_reach": actual_reach,
                "guaranteed_reach": package.guaranteed_reach,
                "difference": actual_reach - package.guaranteed_reach,
                "meets_guarantee": actual_reach >= package.guaranteed_reach,
            }

    def calculate_package_discount(
        self,
        package_id: int,
    ) -> dict[str, Any]:
        """
        Рассчитать скидку пакета по сравнению с разовыми размещениями.

        Args:
            package_id: ID пакета.

        Returns:
            dict с regular_price, package_price, discount_amount, discount_pct.
        """
        # Заглушка — в реальности нужно считать сумму разовых размещений
        # по всем каналам пакета
        return {
            "package_id": package_id,
            "regular_price": 0,  # Placeholder
            "package_price": 0,  # Placeholder
            "discount_amount": 0,
            "discount_pct": 0,
        }


# Глобальный экземпляр
b2b_package_service = B2BPackageService()
