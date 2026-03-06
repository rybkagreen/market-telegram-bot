"""
Репозиторий для работы с аналитикой Telegram чатов.
"""

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import desc

from src.db.models.analytics import ChatSnapshot, ChatType, TelegramChat
from src.db.models.campaign import Campaign


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
        subcategory: str | None = None,
        recent_posts: list[dict] | None = None,
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
            subcategory: Подкатегория канала (автоклассификация).
            recent_posts: Последние посты для LLM-классификации.
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
        if subcategory is not None:
            values["subcategory"] = subcategory
        if recent_posts is not None:
            values["recent_posts"] = recent_posts
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
        order_expr = order_map.get(order_by, TelegramChat.last_subscribers.desc())
        q = q.order_by(order_expr)  # type: ignore[arg-type]
        q = q.limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_top_topic(self, user_id: int) -> str | None:
        """
        Получить тематику с наибольшим числом успешных кампаний у пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Топовая тематика или None.
        """
        result = await self._session.execute(
            select(Campaign.topic, func.count(Campaign.id).label("cnt"))
            .where(
                Campaign.user_id == user_id,
                Campaign.status == "done",
                Campaign.topic.isnot(None),
            )
            .group_by(Campaign.topic)
            .order_by(desc("cnt"))
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None

    async def get_chats_for_mailing(
        self,
        topic: str | None = None,
        min_members: int = 100,
        max_members: int | None = None,
        limit: int = 100,
    ) -> list[TelegramChat]:
        """
        Выборка чатов для рассылки с фильтрами.
        Заменяет ChatRepository.select_chats_for_mailing().

        Args:
            topic: Тематика для фильтрации.
            min_members: Минимальное количество участников.
            max_members: Максимальное количество участников.
            limit: Максимальное количество результатов.

        Returns:
            Список чатов подходящих для рассылки.
        """
        # Спринт 0: фильтр только по каналам где бот добавлен админом и принимает рекламу
        q = select(TelegramChat).where(
            TelegramChat.is_active,
            TelegramChat.is_scam.is_(False),
            TelegramChat.is_fake.is_(False),
            TelegramChat.error_count < 5,
            TelegramChat.member_count >= min_members,
            TelegramChat.bot_is_admin,  # Спринт 0: только opt-in каналы
            TelegramChat.is_accepting_ads,  # Спринт 0: только принимающие рекламу
        )
        if topic:
            q = q.where(TelegramChat.topic == topic)
        if max_members:
            q = q.where(TelegramChat.member_count <= max_members)
        q = q.order_by(TelegramChat.rating.desc()).limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def increment_error(self, chat_id: int, reason: str | None = None) -> None:
        """
        Увеличить счётчик ошибок.
        После 5 ошибок — деактивировать чат.

        Args:
            chat_id: ID чата в БД.
            reason: Причина ошибки.
        """
        chat = await self._session.get(TelegramChat, chat_id)
        if chat:
            chat.increment_error(reason)
            await self._session.flush()

    async def count_blacklisted(self) -> int:
        """
        Количество каналов в чёрном списке.

        Returns:
            Количество каналов.
        """
        stmt = select(func.count(TelegramChat.id)).where(TelegramChat.is_blacklisted == True)  # noqa: E712
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def get_blacklisted(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[TelegramChat], int]:
        """
        Список заблокированных каналов с общим количеством.

        Args:
            offset: Смещение.
            limit: Максимальное количество.

        Returns:
            Кортеж (список каналов, общее количество).
        """
        count_stmt = select(func.count(TelegramChat.id)).where(TelegramChat.is_blacklisted == True)  # noqa: E712
        total = (await self._session.execute(count_stmt)).scalar_one() or 0

        stmt = (
            select(TelegramChat)
            .where(TelegramChat.is_blacklisted == True)  # noqa: E712
            .order_by(TelegramChat.blacklisted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def unblacklist(self, chat_db_id: int) -> None:
        """
        Снять блокировку с канала.

        Args:
            chat_db_id: ID канала в БД.
        """
        chat = await self._session.get(TelegramChat, chat_db_id)
        if not chat:
            return
        chat.is_blacklisted = False
        chat.is_active = True
        chat.blacklisted_reason = None
        chat.blacklisted_at = None
        chat.complaint_count = 0
        await self._session.commit()
