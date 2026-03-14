"""
ChannelSettings Repository для работы с настройками каналов.
Расширяет BaseRepository специфичными методами для ChannelSettings.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.channel_settings import ChannelSettings
from src.db.repositories.base import BaseRepository


class ChannelSettingsRepo(BaseRepository[ChannelSettings]):
    """
    Репозиторий для работы с настройками каналов.
    """

    model = ChannelSettings

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_by_channel(self, channel_id: int) -> ChannelSettings | None:
        """
        Получить настройки канала. None если не существует.

        Args:
            channel_id: ID канала.

        Returns:
            Настройки канала или None.
        """
        return await self.session.get(self.model, channel_id)

    async def get_or_create_default(self, channel_id: int, owner_id: int) -> ChannelSettings:
        """
        Получить настройки или создать с дефолтными значениями.
        Дефолты из ChannelSettings.* констант.

        Args:
            channel_id: ID канала.
            owner_id: ID владельца канала.

        Returns:
            Настройки канала.
        """
        settings = await self.get_by_channel(channel_id)

        if settings is not None:
            return settings

        # Создаём с дефолтными значениями
        attributes = {
            "channel_id": channel_id,
            "owner_id": owner_id,
            "price_per_post": Decimal("500.00"),
            "daily_package_enabled": True,
            "daily_package_max": 2,
            "daily_package_discount": 20,
            "weekly_package_enabled": True,
            "weekly_package_max": 5,
            "weekly_package_discount": 30,
            "subscription_enabled": True,
            "subscription_min_days": 7,
            "subscription_max_days": 365,
            "subscription_max_per_day": 1,
            "publish_start_time": "09:00:00",
            "publish_end_time": "21:00:00",
            "break_start_time": "14:00:00",
            "break_end_time": "15:00:00",
            "auto_accept_enabled": False,
        }

        return await self.create(attributes)

    async def upsert(
        self,
        channel_id: int,
        owner_id: int,
        **kwargs: Any,
    ) -> ChannelSettings:
        """
        Создать или обновить настройки.
        kwargs — любые поля ChannelSettings.
        Валидация ограничений выполняется в сервисе, не здесь.

        Args:
            channel_id: ID канала.
            owner_id: ID владельца канала.
            **kwargs: Поля для обновления/создания.

        Returns:
            Настройки канала.
        """
        settings = await self.get_by_channel(channel_id)

        if settings is not None:
            # Обновляем существующие
            for key, value in kwargs.items():
                if value is not None and hasattr(settings, key):
                    setattr(settings, key, value)

            await self.session.flush()
            await self.session.refresh(settings)
            return settings

        # Создаём новые
        attributes = {
            "channel_id": channel_id,
            "owner_id": owner_id,
            **kwargs,
        }

        return await self.create(attributes)

    async def get_by_owner(self, owner_id: int) -> list[ChannelSettings]:
        """
        Все настройки каналов владельца.

        Args:
            owner_id: ID владельца канала.

        Returns:
            Список настроек каналов.
        """
        query = (
            select(self.model)
            .where(self.model.owner_id == owner_id)
            .order_by(self.model.channel_id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(self, channel_id: int) -> bool:
        """
        Удалить настройки (при удалении канала). True если удалено.

        Args:
            channel_id: ID канала.

        Returns:
            True если удалено, False если не найдено.
        """
        settings = await self.get_by_channel(channel_id)
        if settings is None:
            return False

        await self.session.delete(settings)
        await self.session.flush()
        return True
