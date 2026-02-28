"""
Telegram Parser для поиска и валидации публичных чатов.
Использует Telethon (User API) для поиска каналов и чатов.
"""

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC
from typing import Any

import httpx
from bs4 import BeautifulSoup
from redis.asyncio import Redis
from telethon import TelegramClient
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import (
    Channel,
    Chat,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatInfo:
    """Информация о чате/канале."""

    telegram_id: int
    title: str
    username: str | None
    description: str | None
    member_count: int
    is_verified: bool
    is_scam: bool
    is_fake: bool
    is_broadcast: bool
    linked_chat_id: int | None = None
    can_view_participants: bool = False
    can_send_messages: bool = False


@dataclass
class ChatDetails:
    """Детальная информация о чате после полной проверки."""

    telegram_id: int
    title: str
    username: str | None
    description: str | None
    member_count: int
    topic: str | None
    is_verified: bool
    is_scam: bool
    is_fake: bool
    is_broadcast: bool
    is_active: bool
    rating: float
    avg_post_reach: int | None
    posts_per_day: float
    last_checked: float | None = None


@dataclass
class ChatFullInfo:
    """
    Унифицированная модель данных Telegram чата.
    Объединяет поля ChatInfo + ChatDetails + ChatMetrics.
    Используется во всех слоях: парсер → репозиторий → обработчик.
    """

    # Идентификация
    telegram_id: int
    username: str
    title: str
    description: str | None = None

    # Тип и доступность
    chat_type: str = "channel"  # channel | group | supergroup
    is_public: bool = True
    can_post: bool = False

    # Метаданные TGStat/Telegram
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False
    rating: float = 0.0

    # Метрики (заполняются при полном парсинге)
    subscribers: int = 0
    avg_views: int = 0
    max_views: int = 0
    min_views: int = 0
    posts_analyzed: int = 0
    er: float = 0.0
    post_frequency: float = 0.0  # постов в день за 30 дней
    posts_last_30d: int = 0

    # Статус парсинга
    error: str | None = None

    @classmethod
    def from_chat_info(cls, info: ChatInfo) -> "ChatFullInfo":
        """Конвертер из ChatInfo (для обратной совместимости)."""
        return cls(
            telegram_id=info.telegram_id,
            username=info.username or "",
            title=info.title,
            description=info.description,
            is_verified=info.is_verified,
            is_scam=info.is_scam,
            is_fake=info.is_fake,
            subscribers=info.member_count,
        )

    @classmethod
    def from_chat_details(cls, details: ChatDetails) -> "ChatFullInfo":
        """Конвертер из ChatDetails (для обратной совместимости)."""
        return cls(
            telegram_id=details.telegram_id,
            username=details.username or "",
            title=details.title,
            description=details.description,
            is_verified=details.is_verified,
            is_scam=details.is_scam,
            is_fake=details.is_fake,
            rating=details.rating,
            subscribers=details.member_count,
            avg_views=details.avg_post_reach or 0,
            post_frequency=details.posts_per_day,
        )


class TelegramParser:
    """
    Парсер Telegram для поиска и валидации публичных чатов.

    Использование:
        parser = TelegramParser()
        await parser.start()
        chats = await parser.search_public_chats("бизнес", limit=50)
        await parser.stop()
    """

    # Кэширование в Redis
    CACHE_TTL: int = 3600  # 1 час для метрик чатов
    CACHE_TTL_LONG: int = 86400  # 24 часа для каталогов TGStat

    def __init__(self, redis: Redis | None = None) -> None:
        """
        Инициализация парсера.

        Args:
            redis: Redis клиент для кэширования (опционально).
        """
        self._client: TelegramClient | None = None
        self._is_started = False
        self._redis: Redis | None = redis

    async def start(self) -> None:
        """
        Запустить клиент Telethon.

        Raises:
            RuntimeError: Если клиент уже запущен.
            ValueError: Если TELETHON_SESSION_STRING не задан.
        """
        if self._is_started:
            raise RuntimeError("Parser already started")

        if not settings.telethon_session_string:
            raise ValueError(
                "TELETHON_SESSION_STRING не задан в .env. "
                "Запусти scripts/create_session.py для генерации."
            )

        self._client = TelegramClient(
            StringSession(settings.telethon_session_string),
            settings.api_id,
            settings.api_hash,
        )

        await self._client.start(bot_token=settings.bot_token)
        self._is_started = True
        logger.info("Telegram parser started")

    async def stop(self) -> None:
        """
        Остановить клиент Telethon.
        """
        if self._client and self._is_started:
            await self._client.disconnect()
            self._is_started = False
            logger.info("Telegram parser stopped")

    async def __aenter__(self) -> "TelegramParser":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Async context manager exit."""
        await self.stop()

    # ──────────────────────────────────────────────────────
    # Методы кэширования в Redis
    # ──────────────────────────────────────────────────────

    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Создать ключ кэша."""
        return f"parser:{prefix}:{identifier.lower()}"

    async def _cache_get(self, key: str) -> Any | None:
        """Получить из кэша."""
        if not self._redis:
            return None
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        return None

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Сохранить в кэш."""
        if not self._redis:
            return
        try:
            ttl = ttl or self.CACHE_TTL
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.debug(f"Cache set error: {e}")

    async def _cache_delete(self, key: str) -> None:
        """Удалить из кэша."""
        if not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.debug(f"Cache delete error: {e}")

    async def _cache_invalidate_pattern(self, pattern: str) -> None:
        """Удалить ключи по паттерну."""
        if not self._redis:
            return
        try:
            keys = []
            async for key in self._redis.scan_iter(f"parser:{pattern}*"):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
        except Exception as e:
            logger.debug(f"Cache invalidate error: {e}")

    # ──────────────────────────────────────────────────────
    # Методы поиска и валидации
    # ──────────────────────────────────────────────────────

    @property
    def client(self) -> TelegramClient:
        """Получить клиент Telethon."""
        if not self._client or not self._is_started:
            raise RuntimeError("Parser not started. Call start() first.")
        return self._client

    async def search_public_chats(
        self,
        query: str,
        limit: int = 50,
    ) -> list[ChatInfo]:
        """
        Искать публичные каналы по запросу.

        Args:
            query: Поисковый запрос (например, "бизнес", "новости").
            limit: Максимальное количество результатов.

        Returns:
            Список найденных чатов.
        """
        results: list[ChatInfo] = []

        try:
            # Поиск через Telegram
            search_results = await self.client.get_entity(query)

            if isinstance(search_results, list):
                entities = search_results[:limit]
            else:
                entities = [search_results]

            for entity in entities:
                chat_info = await self._process_entity(entity)
                if chat_info:
                    results.append(chat_info)

        except FloodWaitError as e:
            logger.warning(f"FloodWait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")

        return results

    async def resolve_and_validate(self, username: str) -> ChatDetails | None:
        """
        Разрешить username и полностью проверить чат.

        Args:
            username: Username канала (например, "business_news").

        Returns:
            ChatDetails или None если чат не подходит.
        """
        try:
            # Убираем @ если есть
            username = username.lstrip("@")

            # Получаем entity
            entity = await self.client.get_entity(username)

            if not isinstance(entity, Channel):
                logger.warning(f"{username} is not a channel")
                return None

            # Проверка на restrictions
            if entity.restricted:
                logger.warning(f"{username} is restricted")
                return None

            # Проверка что это канал (не группа и не пользователь)
            if not entity.broadcast:
                logger.info(f"{username} is not a broadcast channel")

            # Получаем полную информацию
            full_channel = await self.client(GetFullChannelRequest(entity))

            return await self._create_chat_details(entity, full_channel)

        except (ChannelInvalidError, ChannelPrivateError):
            logger.warning(f"Channel {username} is invalid or private")
            return None
        except FloodWaitError as e:
            logger.warning(f"FloodWait for {username}: {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
            return None
        except Exception as e:
            logger.error(f"Error resolving {username}: {e}")
            return None

    async def batch_validate(
        self,
        usernames: list[str],
        semaphore_count: int = 10,
    ) -> list[ChatDetails]:
        """
        Пакетная проверка списка username.

        Args:
            usernames: Список username для проверки.
            semaphore_count: Количество одновременных запросов.

        Returns:
            Список валидных ChatDetails.
        """
        semaphore = asyncio.Semaphore(semaphore_count)
        results: list[ChatDetails] = []

        async def validate_with_semaphore(username: str) -> None:
            async with semaphore:
                result = await self.resolve_and_validate(username)
                if result:
                    results.append(result)
                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)

        tasks = [validate_with_semaphore(username) for username in usernames]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def _process_entity(self, entity: Any) -> ChatInfo | None:
        """
        Обработать entity и вернуть ChatInfo.

        Args:
            entity: Telegram entity.

        Returns:
            ChatInfo или None.
        """
        if not isinstance(entity, Channel):
            return None

        # Проверка что канал публичный
        if not entity.username:
            logger.debug(f"Channel {entity.title} is private (no username)")
            return None

        try:
            full_channel = await self.client(GetFullChannelRequest(entity))

            return ChatInfo(
                telegram_id=entity.id,
                title=entity.title,
                username=entity.username,
                description=getattr(full_channel.full_chat, "about", None),
                member_count=getattr(full_channel.full_chat, "participants_count", 0),
                is_verified=entity.verified,
                is_scam=entity.scam,
                is_fake=entity.fake,
                is_broadcast=entity.broadcast,
                linked_chat_id=getattr(full_channel.full_chat, "linked_chat_id", None),
                can_view_participants=True,
                can_send_messages=getattr(full_channel.full_chat, "participants_admin_rights", None)
                is None,
            )

        except Exception as e:
            logger.error(f"Error processing entity {entity.title}: {e}")
            return None

    async def _create_chat_details(
        self,
        entity: Channel,
        full_channel: GetFullChannelRequest,
    ) -> ChatDetails:
        """
        Создать ChatDetails из entity и полной информации.

        Args:
            entity: Channel entity.
            full_channel: Полная информация о канале.

        Returns:
            ChatDetails.
        """
        from datetime import datetime

        full_chat = full_channel.full_chat

        # Базовая валидация
        is_active = (
            not entity.restricted
            and not entity.scam
            and not entity.fake
            and getattr(full_chat, "participants_count", 0) >= 100
        )

        return ChatDetails(
            telegram_id=entity.id,
            title=entity.title,
            username=entity.username,
            description=getattr(full_chat, "about", None),
            member_count=getattr(full_chat, "participants_count", 0),
            topic=None,  # Будет определена в topic_classifier
            is_verified=entity.verified,
            is_scam=entity.scam,
            is_fake=entity.fake,
            is_broadcast=entity.broadcast,
            is_active=is_active,
            rating=5.0,  # Default rating
            avg_post_reach=None,  # Может быть обновлен позже
            posts_per_day=0.0,  # Может быть обновлен позже
            last_checked=datetime.now(tz=UTC).timestamp(),
        )

    async def get_chat_members_count(self, chat_id: int) -> int:
        """
        Получить количество участников чата.

        Args:
            chat_id: Telegram ID чата.

        Returns:
            Количество участников.
        """
        try:
            entity = await self.client.get_entity(chat_id)
            match entity:
                case Channel() | Chat():
                    return getattr(entity, "participants_count", 0)
        except Exception as e:
            logger.error(f"Error getting members count for {chat_id}: {e}")
        return 0

    # ──────────────────────────────────────────────────────
    # Методы сбора метрик
    # ──────────────────────────────────────────────────────

    # Константы для метрик
    POSTS_SAMPLE: int = 30  # постов для расчёта avg_views
    FREQUENCY_DAYS: int = 30  # дней для расчёта частоты публикаций
    REQUEST_DELAY: float = 2.0  # секунд между запросами

    async def parse_chat_metrics(self, username: str) -> ChatFullInfo:
        """
        Собрать полные метрики чата: подписчики, просмотры, ER, частота.
        Включает FloodWait handling и retry логику.
        Кэширует результат в Redis на 1 час.

        Args:
            username: Username канала (с @ или без).

        Returns:
            ChatFullInfo с метриками или error полем.
        """
        username = username.lstrip("@").lower()

        # Проверяем кэш
        cache_key = self._get_cache_key("metrics", username)
        cached = await self._cache_get(cache_key)
        if cached:
            logger.debug(f"Cache hit for @{username}")
            return ChatFullInfo(**cached)

        try:
            result = await self._collect_full_metrics(username)

            # Кэшируем только успешный результат
            if not result.error:
                await self._cache_set(cache_key, asdict(result), self.CACHE_TTL)

            return result
        except FloodWaitError as e:
            wait_sec = e.seconds + 5
            logger.warning(f"FloodWait {wait_sec}s для @{username}, жду...")
            await asyncio.sleep(wait_sec)
            try:
                return await self._collect_full_metrics(username)
            except Exception as retry_err:
                return self._error_result(username, str(retry_err))
        except (ChannelPrivateError, UsernameNotOccupiedError, UsernameInvalidError) as e:
            return self._error_result(username, f"Недоступен: {type(e).__name__}")
        except Exception as e:
            logger.error(f"Ошибка парсинга @{username}: {e}")
            return self._error_result(username, str(e)[:200])

    async def _collect_full_metrics(self, username: str) -> ChatFullInfo:
        """Внутренний метод: собрать все данные для одного чата."""
        await self._rate_limit()
        entity = await self.client.get_entity(username)
        await self._rate_limit()

        full = await self.client(GetFullChannelRequest(entity))
        await self._rate_limit()

        chat_type, can_post, is_public = self._detect_chat_type(entity, full)
        subscribers = getattr(full.full_chat, "participants_count", 0) or 0
        description = getattr(full.full_chat, "about", "") or ""
        title = getattr(entity, "title", username)
        telegram_id = entity.id

        posts_data = await self._collect_posts_metrics(entity)
        await self._rate_limit()
        frequency, posts_30d = await self._collect_post_frequency(entity)

        er = 0.0
        if subscribers > 0 and posts_data["avg_views"] > 0:
            er = round(posts_data["avg_views"] / subscribers * 100, 2)

        return ChatFullInfo(
            username=username,
            telegram_id=telegram_id,
            title=title,
            description=description,
            chat_type=chat_type,
            is_public=is_public,
            can_post=can_post,
            subscribers=subscribers,
            avg_views=posts_data["avg_views"],
            max_views=posts_data["max_views"],
            min_views=posts_data["min_views"],
            posts_analyzed=posts_data["count"],
            er=er,
            post_frequency=frequency,
            posts_last_30d=posts_30d,
        )

    async def _rate_limit(self) -> None:
        """Пауза между запросами для соблюдения лимитов Telegram API."""
        now = asyncio.get_event_loop().time()
        elapsed = now - getattr(self, "_last_request_time", 0.0)
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    def _detect_chat_type(self, entity: Channel | Chat, full: Any) -> tuple[str, bool, bool]:
        """
        Определить тип чата и возможность постинга.

        Args:
            entity: Channel или Chat entity.
            full: Полная информация о канале.

        Returns:
            Кортеж (chat_type, can_post, is_public).
        """
        is_megagroup = getattr(entity, "megagroup", False)
        is_broadcast = getattr(entity, "broadcast", False)
        default_ban_rights = getattr(full.full_chat, "default_banned_rights", None)

        if is_broadcast:
            chat_type, can_post = "channel", False
        elif is_megagroup:
            chat_type = "supergroup"
            can_post = (
                not getattr(default_ban_rights, "send_messages", True)
                if default_ban_rights
                else True
            )
        else:
            chat_type, can_post = "group", True

        is_public = bool(getattr(entity, "username", None))
        return chat_type, can_post, is_public

    async def _collect_posts_metrics(self, entity: Channel | Chat) -> dict:
        """
        Собрать метрики просмотров по последним N постам.

        Args:
            entity: Channel или Chat entity.

        Returns:
            Dict с полями avg_views, max_views, min_views, count.
        """
        views_list = []
        try:
            async for message in self.client.iter_messages(entity, limit=self.POSTS_SAMPLE):
                if message.views and message.views > 0:
                    views_list.append(message.views)
        except Exception as e:
            logger.debug(f"Не удалось получить посты: {e}")

        if not views_list:
            return {"avg_views": 0, "max_views": 0, "min_views": 0, "count": 0}

        return {
            "avg_views": int(sum(views_list) / len(views_list)),
            "max_views": max(views_list),
            "min_views": min(views_list),
            "count": len(views_list),
        }

    async def _collect_post_frequency(self, entity: Channel | Chat) -> tuple[float, int]:
        """
        Частота публикаций за последние 30 дней.

        Args:
            entity: Channel или Chat entity.

        Returns:
            Кортеж (posts_per_day, total_posts_30d).
        """
        from datetime import datetime, timedelta

        since = datetime.now(tz=UTC) - timedelta(days=self.FREQUENCY_DAYS)
        count = 0
        try:
            async for message in self.client.iter_messages(entity):
                if message.date < since:
                    break
                if not message.action:
                    count += 1
        except Exception as e:
            logger.debug(f"Ошибка подсчёта частоты: {e}")
        return round(count / self.FREQUENCY_DAYS, 2), count

    async def parse_chats_batch(
        self,
        usernames: list[str],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[ChatFullInfo]:
        """
        Парсить батч чатов через единый клиент.
        Заменяет parse_chats_batch() из chat_parser.py.

        Args:
            usernames: Список username для парсинга.
            on_progress: Callback(done, total) для логирования.

        Returns:
            Список ChatFullInfo.
        """
        results = []
        for i, username in enumerate(usernames):
            result = await self.parse_chat_metrics(username)
            results.append(result)
            if on_progress:
                on_progress(i + 1, len(usernames))
        return results

    @staticmethod
    def _error_result(username: str, error: str) -> ChatFullInfo:
        """Создать ChatFullInfo с ошибкой."""
        return ChatFullInfo(
            username=username,
            telegram_id=0,
            title=username,
            error=error,
        )

    # ──────────────────────────────────────────────────────
    # TGStat методы (перенесено из tgstat_parser.py)
    # ──────────────────────────────────────────────────────

    # Base URL для каталогов TGStat
    TGSTAT_BASE_URL: str = "https://tgstat.ru"
    TGSTAT_REQUEST_DELAY: float = 2.0  # секунды между запросами
    TGSTAT_TIMEOUT: int = 30  # таймаут запроса

    # User-Agent для обхода простых защит
    TGSTAT_HEADERS: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    async def _get_tgstat_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP клиент для TGStat."""
        client = httpx.AsyncClient(
            headers=self.TGSTAT_HEADERS,
            timeout=httpx.Timeout(self.TGSTAT_TIMEOUT),
            follow_redirects=True,
        )
        return client

    async def fetch_tgstat_catalog(
        self,
        topic: str,
        max_pages: int = 5,
    ) -> list[str]:
        """
        Получить список username каналов из каталога TGStat.
        Кэширует результат в Redis на 24 часа.

        Args:
            topic: Тематика (например, "business", "news", "crypto").
            max_pages: Максимальное количество страниц для парсинга.

        Returns:
            Список username (без @).
        """
        # Проверяем кэш
        cache_key = self._get_cache_key("tgstat", topic)
        cached = await self._cache_get(cache_key)
        if cached:
            logger.debug(f"Cache hit for TGStat topic '{topic}'")
            return cached

        usernames: list[str] = []
        client = await self._get_tgstat_client()

        try:
            catalog_url = f"{self.TGSTAT_BASE_URL}/catalog/{topic}"

            for page in range(1, max_pages + 1):
                page_url = f"{catalog_url}?p={page}" if page > 1 else catalog_url

                try:
                    response = await client.get(page_url)
                    response.raise_for_status()

                    usernames_on_page = self._parse_tgstat_catalog_page(response.text)

                    if not usernames_on_page:
                        logger.info(f"No more channels found on page {page}")
                        break

                    usernames.extend(usernames_on_page)
                    logger.info(f"Found {len(usernames_on_page)} channels on page {page}")

                    if page < max_pages:
                        await asyncio.sleep(self.TGSTAT_REQUEST_DELAY)

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error on page {page}: {e}")
                    break
                except httpx.RequestError as e:
                    logger.error(f"Request error on page {page}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error on page {page}: {e}")
                    break

            logger.info(f"Total found {len(usernames)} channels for topic '{topic}'")
            result = list(set(usernames))

            # Кэшируем результат
            await self._cache_set(cache_key, result, self.CACHE_TTL_LONG)

            return result
        finally:
            await client.aclose()

    def _parse_tgstat_catalog_page(self, html: str) -> list[str]:
        """
        Распарсить HTML страницу каталога TGStat.

        Args:
            html: HTML содержимое страницы.

        Returns:
            Список username.
        """
        usernames = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            channel_cards = soup.find_all("a", href=re.compile(r"^/channel/"))

            for card in channel_cards:
                href = str(card.get("href") or "")
                match = re.search(r"/channel/@?([a-zA-Z0-9_]+)", href)
                if match:
                    username = match.group(1)
                    if username not in ("search", "popular", "new"):
                        usernames.append(username)

            channel_links = soup.find_all(attrs={"data-channel-url": re.compile(r"^/channel/")})

            for link in channel_links:
                url = str(link.get("data-channel-url") or "")
                match = re.search(r"/channel/@?([a-zA-Z0-9_]+)", url)
                if match:
                    username = match.group(1)
                    if username not in ("search", "popular", "new"):
                        usernames.append(username)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return usernames

    async def fetch_channel_stats(self, username: str) -> dict[str, Any]:
        """
        Получить статистику канала с TGStat.

        Args:
            username: Username канала.

        Returns:
            Словарь со статистикой.
        """
        client = await self._get_tgstat_client()
        url = f"{self.TGSTAT_BASE_URL}/channel/@{username}"

        try:
            response = await client.get(url)
            response.raise_for_status()
            return self._parse_tgstat_channel_stats(response.text)
        except Exception as e:
            logger.error(f"Error fetching stats for @{username}: {e}")
            return {}
        finally:
            await client.aclose()

    def _parse_tgstat_channel_stats(self, html: str) -> dict[str, Any]:
        """
        Распарсить статистику канала с TGStat.

        Args:
            html: HTML содержимое страницы канала.

        Returns:
            Словарь со статистикой.
        """
        stats = {
            "subscribers": 0,
            "avg_post_reach": 0,
            "posts_per_day": 0.0,
            "err_index": 0.0,
        }

        try:
            soup = BeautifulSoup(html, "html.parser")
            stat_blocks = soup.find_all(
                "div", class_=re.compile(r"stat|metric|value", re.IGNORECASE)
            )

            for block in stat_blocks:
                text = block.get_text(strip=True).lower()

                if "подписчик" in text or "subscriber" in text:
                    num_match = re.search(r"([\d\s,\.]+)", text)
                    if num_match:
                        num_str = num_match.group(1).replace(",", "").replace(" ", "")
                        with contextlib.suppress(ValueError):
                            stats["subscribers"] = int(float(num_str))

                if "охват" in text or "reach" in text:
                    num_match = re.search(r"([\d\s,\.]+)", text)
                    if num_match:
                        num_str = num_match.group(1).replace(",", "").replace(" ", "")
                        with contextlib.suppress(ValueError):
                            stats["avg_post_reach"] = int(float(num_str))

        except Exception as e:
            logger.error(f"Error parsing channel stats: {e}")

        return stats

    async def get_all_tgstat_topics(self) -> list[str]:
        """
        Получить список всех доступных тематик на TGStat.

        Returns:
            Список тематик.
        """
        client = await self._get_tgstat_client()

        try:
            response = await client.get(f"{self.TGSTAT_BASE_URL}/catalog")
            response.raise_for_status()
            return self._parse_tgstat_topics(response.text)
        except Exception as e:
            logger.error(f"Error fetching topics: {e}")
            return []
        finally:
            await client.aclose()

    def _parse_tgstat_topics(self, html: str) -> list[str]:
        """
        Распарсить список тематик TGStat.

        Args:
            html: HTML содержимое страницы каталога.

        Returns:
            Список тематик.
        """
        topics = []

        try:
            soup = BeautifulSoup(html, "html.parser")
            topic_links = soup.find_all("a", href=re.compile(r"^/catalog/[a-z]+"))

            for link in topic_links:
                href = str(link.get("href") or "")
                match = re.search(r"/catalog/([a-z-]+)", href)
                if match:
                    topic = match.group(1)
                    if topic not in ("all", "popular", "new"):
                        topics.append(topic)

        except Exception as e:
            logger.error(f"Error parsing topics: {e}")

        return list(set(topics))


# Популярные тематики для парсинга
POPULAR_TOPICS = [
    "business",
    "news",
    "crypto",
    "marketing",
    "it",
    "finance",
    "education",
    "lifestyle",
    "health",
    "sport",
    "auto",
    "travel",
    "food",
    "fashion",
    "real-estate",
]
