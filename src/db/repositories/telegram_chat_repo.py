"""TelegramChatRepository for TelegramChat model operations."""

from typing import Any

from sqlalchemy import and_, select

from src.db.models.telegram_chat import TelegramChat
from src.db.repositories.base import BaseRepository


class TelegramChatRepository(BaseRepository[TelegramChat]):
    """Репозиторий для работы с Telegram каналами."""

    model = TelegramChat

    async def get_by_telegram_id(self, telegram_id: int) -> TelegramChat | None:
        """Получить канал по Telegram ID."""
        result = await self.session.execute(select(TelegramChat).where(TelegramChat.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: int) -> list[TelegramChat]:
        """Получить все активные каналы владельца."""
        result = await self.session.execute(
            select(TelegramChat).where(
                TelegramChat.owner_id == owner_id,
                TelegramChat.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_by_category(
        self,
        category: str | None,
        subcategory: str | None,
        exclude_owner_id: int | None,
    ) -> list[TelegramChat]:
        """Получить каналы по категории."""
        conditions: list[Any] = [TelegramChat.is_active.is_(True)]
        if category:
            conditions.append(TelegramChat.category == category)
        if subcategory:
            conditions.append(TelegramChat.subcategory == subcategory)
        if exclude_owner_id:
            conditions.append(TelegramChat.owner_id != exclude_owner_id)

        result = await self.session.execute(
            select(TelegramChat).where(and_(*conditions)).order_by(TelegramChat.rating.desc())
        )
        return list(result.scalars().all())

    async def get_active(self) -> list[TelegramChat]:
        """Получить все активные каналы."""
        result = await self.session.execute(
            select(TelegramChat).where(TelegramChat.is_active.is_(True)).order_by(TelegramChat.rating.desc())
        )
        return list(result.scalars().all())
