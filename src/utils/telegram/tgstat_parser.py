"""
TGStat.ru Parser для получения каталогов Telegram-каналов.
Парсит публичные каталоги tgstat.ru для поиска каналов по тематикам.
"""

import asyncio
import contextlib
import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TGStatParser:
    """
    Парсер каталога TGStat.ru.

    Использование:
        parser = TGStatParser()
        usernames = await parser.fetch_tgstat_catalog("business")
    """

    # Base URL для каталогов
    BASE_URL = "https://tgstat.ru"

    # Задержки для уважения robots.txt
    REQUEST_DELAY = 2.0  # секунды между запросами
    TIMEOUT = 30  # таймаут запроса

    # User-Agent для обхода простых защит
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(self) -> None:
        """Инициализация парсера."""
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP клиент."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.HEADERS,
                timeout=httpx.Timeout(self.TIMEOUT),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Закрыть HTTP клиент."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "TGStatParser":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def fetch_tgstat_catalog(
        self,
        topic: str,
        max_pages: int = 5,
    ) -> list[str]:
        """
        Получить список username каналов из каталога TGStat.

        Args:
            topic: Тематика (например, "business", "news", "crypto").
            max_pages: Максимальное количество страниц для парсинга.

        Returns:
            Список username (без @).
        """
        usernames: list[str] = []
        client = await self._get_client()

        # URL каталога по тематике
        catalog_url = f"{self.BASE_URL}/catalog/{topic}"

        for page in range(1, max_pages + 1):
            page_url = f"{catalog_url}?p={page}" if page > 1 else catalog_url

            try:
                response = await client.get(page_url)
                response.raise_for_status()

                # Парсим HTML
                usernames_on_page = self._parse_catalog_page(response.text)

                if not usernames_on_page:
                    logger.info(f"No more channels found on page {page}")
                    break

                usernames.extend(usernames_on_page)
                logger.info(f"Found {len(usernames_on_page)} channels on page {page}")

                # Задержка между запросами
                if page < max_pages:
                    await asyncio.sleep(self.REQUEST_DELAY)

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
        return list(set(usernames))  # Убираем дубликаты

    def _parse_catalog_page(self, html: str) -> list[str]:
        """
        Распарсить HTML страницу каталога.

        Args:
            html: HTML содержимое страницы.

        Returns:
            Список username.
        """
        usernames = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Ищем карточки каналов
            # TGStat использует классы вида .channel-card, .catalog-item
            channel_cards = soup.find_all(
                "a",
                href=re.compile(r"^/channel/"),
            )

            for card in channel_cards:
                href = card.get("href", "")
                # Извлекаем username из URL /channel/@username или /channel/username
                match = re.search(r"/channel/@?([a-zA-Z0-9_]+)", href)
                if match:
                    username = match.group(1)
                    # Фильтруем служебные страницы
                    if username not in ("search", "popular", "new"):
                        usernames.append(username)

            # Альтернативный поиск по data-атрибутам
            channel_links = soup.find_all(
                attrs={"data-channel-url": re.compile(r"^/channel/")},
            )

            for link in channel_links:
                url = link.get("data-channel-url", "")
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
        client = await self._get_client()
        url = f"{self.BASE_URL}/channel/@{username}"

        try:
            response = await client.get(url)
            response.raise_for_status()

            return self._parse_channel_stats(response.text)

        except Exception as e:
            logger.error(f"Error fetching stats for @{username}: {e}")
            return {}

    def _parse_channel_stats(self, html: str) -> dict[str, Any]:
        """
        Распарсить статистику канала.

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

            # Ищем блоки со статистикой
            stat_blocks = soup.find_all(
                "div",
                class_=re.compile(r"stat|metric|value", re.IGNORECASE),
            )

            for block in stat_blocks:
                text = block.get_text(strip=True).lower()

                # Подписчики
                if "подписчик" in text or "subscriber" in text:
                    num_match = re.search(r"([\d\s,\.]+)", text)
                    if num_match:
                        num_str = num_match.group(1).replace(",", "").replace(" ", "")
                        with contextlib.suppress(ValueError):
                            stats["subscribers"] = int(float(num_str))

                # Охват
                if "охват" in text or "reach" in text:
                    num_match = re.search(r"([\d\s,\.]+)", text)
                    if num_match:
                        num_str = num_match.group(1).replace(",", "").replace(" ", "")
                        with contextlib.suppress(ValueError):
                            stats["avg_post_reach"] = int(float(num_str))

        except Exception as e:
            logger.error(f"Error parsing channel stats: {e}")

        return stats

    async def get_all_topics(self) -> list[str]:
        """
        Получить список всех доступных тематик.

        Returns:
            Список тематик.
        """
        client = await self._get_client()

        try:
            response = await client.get(f"{self.BASE_URL}/catalog")
            response.raise_for_status()

            return self._parse_topics(response.text)

        except Exception as e:
            logger.error(f"Error fetching topics: {e}")
            return []

    def _parse_topics(self, html: str) -> list[str]:
        """
        Распарсить список тематик.

        Args:
            html: HTML содержимое страницы каталога.

        Returns:
            Список тематик.
        """
        topics = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Ищем ссылки на тематики
            topic_links = soup.find_all(
                "a",
                href=re.compile(r"^/catalog/[a-z]+"),
            )

            for link in topic_links:
                href = link.get("href", "")
                match = re.search(r"/catalog/([a-z-]+)", href)
                if match:
                    topic = match.group(1)
                    # Исключаем служебные
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
