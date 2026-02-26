"""
Репозиторий для работы с аналитикой Telegram чатов.
"""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.analytics import ChatSnapshot, ChatType, TelegramChat


class ChatAnalyticsRepository:
    """
    Репозиторий для работы с аналитикой Telegram чатов.

    Методы:
        get_or_create_chat: Получить чат по username или создать новый.
        get_all_active: Получить все активные чаты для парсинга.
        update_chat_meta: Обновить мета-данные чата после парсинга.
        mark_parse_error: Записать ошибку парсинга.
        upsert_snapshot: Вставить или обновить снимок метрик за день.
        get_snapshots: История снимков за N дней.
        get_top_chats: Топ чатов по метрике.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        self._session = session

    # ─── Чаты ───────────────────────────────────────────

    async def get_or_create_chat(self, username: str) -> tuple[TelegramChat, bool]:
        """
        Получить чат по username или создать новый.

        Args:
            username: Username чата (с @ или без).

        Returns:
            Кортеж (chat, is_new) где is_new=True если чат создан.
        """
        username = username.lstrip("@").lower()
        result = await self._session.execute(
            select(TelegramChat).where(TelegramChat.username == username)
        )
        chat = result.scalar_one_or_none()
        if chat:
            return chat, False
        chat = TelegramChat(username=username)
        self._session.add(chat)
        await self._session.flush()
        return chat, True

    async def get_all_active(self) -> list[TelegramChat]:
        """
        Получить все активные чаты для парсинга.
        Сортировка: дольше не парсились — первые.

        Returns:
            Список активных чатов.
        """
        result = await self._session.execute(
            select(TelegramChat)
            .where(TelegramChat.is_active == True)  # noqa: E712
            .order_by(TelegramChat.last_parsed_at.asc().nulls_first())
        )
        return list(result.scalars().all())

    async def update_chat_meta(
        self,
        chat_id: int,
        *,
        telegram_id: int | None = None,
        title: str | None = None,
        description: str | None = None,
        chat_type: ChatType | None = None,
        can_post: bool | None = None,
        is_public: bool | None = None,
        last_subscribers: int | None = None,
        last_avg_views: int | None = None,
        last_er: float | None = None,
        last_post_frequency: float | None = None,
    ) -> None:
        """
        Обновить мета-данные чата после парсинга.

        Args:
            chat_id: ID чата в БД.
            telegram_id: Telegram ID чата.
            title: Заголовок чата.
            description: Описание чата.
            chat_type: Тип чата.
            can_post: Можно ли постить.
            is_public: Публичный ли чат.
            last_subscribers: Количество подписчиков.
            last_avg_views: Средний охват постов.
            last_er: Engagement Rate.
            last_post_frequency: Частота публикаций.
        """
        values: dict[str, Any] = {
            "updated_at": datetime.utcnow(),
            "parse_error": None,
            "parse_error_count": 0,
        }
        if telegram_id is not None:
            values["telegram_id"] = telegram_id
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if chat_type is not None:
            values["chat_type"] = chat_type
        if can_post is not None:
            values["can_post"] = can_post
        if is_public is not None:
            values["is_public"] = is_public
        if last_subscribers is not None:
            values["last_subscribers"] = last_subscribers
        if last_avg_views is not None:
            values["last_avg_views"] = last_avg_views
        if last_er is not None:
            values["last_er"] = last_er
        if last_post_frequency is not None:
            values["last_post_frequency"] = last_post_frequency
        values["last_parsed_at"] = datetime.utcnow()

        await self._session.execute(
            update(TelegramChat).where(TelegramChat.id == chat_id).values(**values)
        )

    async def mark_parse_error(self, chat_id: int, error: str) -> None:
        """
        Записать ошибку парсинга.
        После 5 ошибок подряд — деактивировать чат.

        Args:
            chat_id: ID чата в БД.
            error: Текст ошибки.
        """
        chat = await self._session.get(TelegramChat, chat_id)
        if not chat:
            return
        chat.parse_error = error[:500]
        chat.parse_error_count = (chat.parse_error_count or 0) + 1
        if chat.parse_error_count >= 5:
            chat.is_active = False
        await self._session.flush()

    # ─── Снимки ─────────────────────────────────────────

    async def upsert_snapshot(
        self,
        chat_id: int,
        snapshot_date: date,
        *,
        subscribers: int,
        avg_views: int,
        max_views: int,
        min_views: int,
        posts_analyzed: int,
        er: float,
        post_frequency: float,
        posts_last_30d: int,
        can_post: bool,
    ) -> ChatSnapshot:
        """
        Вставить или обновить снимок метрик за день.
        Использует PostgreSQL INSERT ON CONFLICT DO UPDATE.

        Args:
            chat_id: ID чата в БД.
            snapshot_date: Дата снимка.
            subscribers: Количество подписчиков.
            avg_views: Средний охват постов.
            max_views: Максимальный охват.
            min_views: Минимальный охват.
            posts_analyzed: Сколько постов проанализировано.
            er: Engagement Rate.
            post_frequency: Частота публикаций.
            posts_last_30d: Количество постов за 30 дней.
            can_post: Можно ли постить.

        Returns:
            Созданный или обновленный ChatSnapshot.
        """
        # Получить предыдущий снимок для расчёта delta
        prev = await self._get_previous_snapshot(chat_id, snapshot_date)
        delta = subscribers - prev.subscribers if prev else 0
        delta_pct = (delta / prev.subscribers * 100) if prev and prev.subscribers else 0.0

        stmt = (
            pg_insert(ChatSnapshot)
            .values(
                chat_id=chat_id,
                snapshot_date=snapshot_date,
                subscribers=subscribers,
                subscribers_delta=delta,
                subscribers_delta_pct=round(delta_pct, 2),
                avg_views=avg_views,
                max_views=max_views,
                min_views=min_views,
                posts_analyzed=posts_analyzed,
                er=round(er, 2),
                post_frequency=round(post_frequency, 2),
                posts_last_30d=posts_last_30d,
                can_post=can_post,
            )
            .on_conflict_do_update(
                index_elements=["chat_id", "snapshot_date"],
                set_={
                    "subscribers": subscribers,
                    "subscribers_delta": delta,
                    "subscribers_delta_pct": round(delta_pct, 2),
                    "avg_views": avg_views,
                    "max_views": max_views,
                    "min_views": min_views,
                    "posts_analyzed": posts_analyzed,
                    "er": round(er, 2),
                    "post_frequency": round(post_frequency, 2),
                    "posts_last_30d": posts_last_30d,
                    "can_post": can_post,
                },
            )
            .returning(ChatSnapshot)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def _get_previous_snapshot(self, chat_id: int, before_date: date) -> ChatSnapshot | None:
        """
        Получить предыдущий снимок для расчёта дельты.

        Args:
            chat_id: ID чата в БД.
            before_date: Дата, до которой искать снимок.

        Returns:
            Предыдущий ChatSnapshot или None.
        """
        result = await self._session.execute(
            select(ChatSnapshot)
            .where(
                and_(
                    ChatSnapshot.chat_id == chat_id,
                    ChatSnapshot.snapshot_date < before_date,
                )
            )
            .order_by(ChatSnapshot.snapshot_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshots(self, chat_id: int, days: int = 30) -> list[ChatSnapshot]:
        """
        История снимков за N дней — для построения графиков.

        Args:
            chat_id: ID чата в БД.
            days: Количество дней.

        Returns:
            Список снимков за последние N дней.
        """
        since = date.today() - timedelta(days=days)
        result = await self._session.execute(
            select(ChatSnapshot)
            .where(
                and_(
                    ChatSnapshot.chat_id == chat_id,
                    ChatSnapshot.snapshot_date >= since,
                )
            )
            .order_by(ChatSnapshot.snapshot_date.asc())
        )
        return list(result.scalars().all())

    async def get_top_chats(
        self,
        topic: str | None = None,
        order_by: str = "subscribers",
        limit: int = 20,
    ) -> list[TelegramChat]:
        """
        Топ чатов по метрике.

        Args:
            topic: Тематика для фильтрации.
            order_by: По какой метрике сортировать.
                      subscribers | er | avg_views | post_frequency
            limit: Максимальное количество результатов.

        Returns:
            Список топ чатов.
        """
        order_map = {
            "subscribers": TelegramChat.last_subscribers.desc(),
            "er": TelegramChat.last_er.desc(),
            "avg_views": TelegramChat.last_avg_views.desc(),
            "post_frequency": TelegramChat.last_post_frequency.desc(),
        }
        q = select(TelegramChat).where(TelegramChat.is_active == True)  # noqa: E712
        if topic:
            q = q.where(TelegramChat.topic == topic)
        q = q.order_by(order_map.get(order_by, TelegramChat.last_subscribers.desc()))
        q = q.limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())
