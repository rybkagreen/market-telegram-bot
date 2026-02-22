"""
Chat Repository для работы с Telegram-чатами.
Расширяет BaseRepository специфичными методами для Chat.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.chat import Chat
from src.db.repositories.base import BaseRepository


@dataclass
class ChatData:
    """Data class для данных чата."""

    telegram_id: int
    title: str
    username: str | None = None
    description: str | None = None
    member_count: int = 0
    topic: str | None = None
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False
    is_broadcast: bool = True
    rating: float = 5.0
    avg_post_reach: int | None = None
    posts_per_day: float = 0.0


class ChatRepository(BaseRepository[Chat]):
    """
    Репозиторий для работы с Telegram-чатами.

    Методы:
        upsert_batch: Пакетная вставка/обновление чатов.
        get_by_telegram_id: Получить чат по Telegram ID.
        get_active_filtered: Получить активные чаты с фильтрами.
        update_rating: Обновить рейтинг чата.
        mark_checked: Отметить чат как проверенный.
        get_for_parser: Получить чаты для парсера.
    """

    model = Chat

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_by_telegram_id(self, telegram_id: int) -> Chat | None:
        """
        Получить чат по Telegram ID.

        Args:
            telegram_id: Telegram ID чата.

        Returns:
            Чат или None.
        """
        return await self.find_one(Chat.telegram_id == telegram_id)

    async def upsert_batch(
        self,
        chats_data: list[ChatData],
        *,
        update_existing: bool = True,
    ) -> int:
        """
        Пакетная вставка или обновление чатов.

        Использует INSERT ... ON CONFLICT DO UPDATE для PostgreSQL.

        Args:
            chats_data: Список данных чатов.
            update_existing: Обновлять ли существующие чаты.

        Returns:
            Количество обработанных чатов.
        """
        if not chats_data:
            return 0

        from sqlalchemy.dialects.postgresql import insert

        processed_count = 0

        for chat_data in chats_data:
            stmt = insert(Chat).values(
                telegram_id=chat_data.telegram_id,
                title=chat_data.title,
                username=chat_data.username,
                description=chat_data.description,
                member_count=chat_data.member_count,
                topic=chat_data.topic,
                is_verified=chat_data.is_verified,
                is_scam=chat_data.is_scam,
                is_fake=chat_data.is_fake,
                is_broadcast=chat_data.is_broadcast,
                rating=chat_data.rating,
                avg_post_reach=chat_data.avg_post_reach,
                posts_per_day=chat_data.posts_per_day,
                last_checked=datetime.now(tz=UTC),
            )

            if update_existing:
                stmt = stmt.on_conflict_do_update(
                    index_elements=[Chat.telegram_id],
                    set_={
                        "title": stmt.excluded.title,
                        "username": stmt.excluded.username,
                        "description": stmt.excluded.description,
                        "member_count": stmt.excluded.member_count,
                        "topic": stmt.excluded.topic,
                        "is_verified": stmt.excluded.is_verified,
                        "is_scam": stmt.excluded.is_scam,
                        "is_fake": stmt.excluded.is_fake,
                        "rating": stmt.excluded.rating,
                        "avg_post_reach": stmt.excluded.avg_post_reach,
                        "posts_per_day": stmt.excluded.posts_per_day,
                        "last_checked": stmt.excluded.last_checked,
                    },
                )

            await self.session.execute(stmt)
            processed_count += 1

        await self.session.flush()
        return processed_count

    async def get_active_filtered(
        self,
        topics: list[str] | None = None,
        min_members: int = 0,
        max_members: int = 1_000_000,
        exclude_ids: list[int] | None = None,
        limit: int = 100,
    ) -> list[Chat]:
        """
        Получить активные чаты с фильтрами.

        Args:
            topics: Список тематик (опционально).
            min_members: Минимальное количество участников.
            max_members: Максимальное количество участников.
            exclude_ids: Исключить эти ID чатов.
            limit: Максимальное количество результатов.

        Returns:
            Список чатов.
        """
        filters = [
            Chat.is_active == True,  # noqa: E712
            Chat.is_scam == False,  # noqa: E712
            Chat.is_fake == False,  # noqa: E712
            Chat.member_count >= min_members,
            Chat.member_count <= max_members,
        ]

        if topics:
            filters.append(Chat.topic.in_(topics))

        if exclude_ids:
            filters.append(Chat.id.notin_(exclude_ids))

        query = (
            select(Chat)
            .where(*filters)
            .order_by(Chat.rating.desc(), Chat.member_count.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_rating(
        self,
        chat_id: int,
        new_rating: float,
    ) -> Chat | None:
        """
        Обновить рейтинг чата.

        Args:
            chat_id: ID чата.
            new_rating: Новый рейтинг (0.0 - 10.0).

        Returns:
            Обновленный чат или None.
        """
        chat = await self.get_by_id(chat_id)
        if chat is None:
            return None

        # Ограничиваем рейтинг диапазоном 0.0 - 10.0
        new_rating = max(0.0, min(10.0, new_rating))

        await self.update(chat_id, {"rating": new_rating})

        # Если рейтинг слишком низкий, деактивируем чат
        if new_rating < 2.0:
            await self.update(
                chat_id,
                {
                    "is_active": False,
                    "deactivate_reason": "Низкий рейтинг",
                },
            )

        await self.refresh(chat)
        return chat

    async def mark_checked(self, chat_id: int) -> Chat | None:
        """
        Отметить чат как проверенный.

        Args:
            chat_id: ID чата.

        Returns:
            Обновленный чат или None.
        """
        await self.update(
            chat_id,
            {"last_checked": datetime.now(tz=UTC)},
        )
        return await self.get_by_id(chat_id)

    async def increment_error_count(
        self,
        chat_id: int,
        error_msg: str | None = None,
    ) -> Chat | None:
        """
        Увеличить счетчик ошибок чата.

        Args:
            chat_id: ID чата.
            error_msg: Сообщение об ошибке.

        Returns:
            Обновленный чат или None.
        """
        chat = await self.get_by_id(chat_id)
        if chat is None:
            return None

        new_error_count = chat.error_count + 1
        update_data: dict[str, Any] = {"error_count": new_error_count}

        # Если слишком много ошибок, деактивируем чат
        if new_error_count >= 5:
            update_data["is_active"] = False
            update_data["deactivate_reason"] = error_msg or "Слишком много ошибок при отправке"

        await self.update(chat_id, update_data)
        await self.refresh(chat)
        return chat

    async def get_for_parser(
        self,
        limit: int = 1000,
    ) -> list[Chat]:
        """
        Получить чаты для обновления данных парсером.

        Возвращает чаты, которые давно не проверялись.

        Args:
            limit: Максимальное количество результатов.

        Returns:
            Список чатов.
        """
        # Чаты, которые не проверялись больше 7 дней
        seven_days_ago = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = seven_days_ago.replace(day=seven_days_ago.day - 7)

        query = (
            select(Chat)
            .where(
                and_(
                    Chat.is_active == True,  # noqa: E712
                    and_(Chat.last_checked.is_(None) | (Chat.last_checked < seven_days_ago)),
                )
            )
            .order_by(Chat.last_checked.asc().nullsfirst())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_statistics(self) -> dict[str, Any]:
        """
        Получить общую статистику по чатам.

        Returns:
            Словарь со статистикой.
        """
        query = select(
            func.count(Chat.id).label("total"),
            func.sum(
                case((Chat.is_active == True, 1), else_=0)  # noqa: E712
            ).label("active"),
            func.sum(
                case((Chat.is_scam == True, 1), else_=0)  # noqa: E712
            ).label("scam"),
            func.sum(
                case((Chat.is_fake == True, 1), else_=0)  # noqa: E712
            ).label("fake"),
            func.avg(Chat.member_count).label("avg_members"),
            func.avg(Chat.rating).label("avg_rating"),
        )

        result = await self.session.execute(query)
        stats = result.one()

        return {
            "total": stats.total or 0,
            "active": stats.active or 0,
            "scam": stats.scam or 0,
            "fake": stats.fake or 0,
            "avg_members": float(stats.avg_members or 0),
            "avg_rating": float(stats.avg_rating or 0),
        }

    async def get_topics_statistics(self) -> list[dict[str, Any]]:
        """
        Получить статистику по тематикам.

        Returns:
            Список словарей со статистикой по каждой тематике.
        """
        query = (
            select(
                Chat.topic,
                func.count(Chat.id).label("count"),
                func.avg(Chat.member_count).label("avg_members"),
                func.avg(Chat.rating).label("avg_rating"),
            )
            .where(Chat.topic.isnot(None))
            .group_by(Chat.topic)
            .order_by(func.count(Chat.id).desc())
        )

        result = await self.session.execute(query)
        return [
            {
                "topic": row.topic,
                "count": row.count,
                "avg_members": float(row.avg_members or 0),
                "avg_rating": float(row.avg_rating or 0),
            }
            for row in result.all()
        ]
