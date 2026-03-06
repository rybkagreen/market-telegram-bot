#!/usr/bin/env python3
"""
Масштабный парсинг Telegram с дедупликацией.
Ищет каналы по расширенному списку запросов.
"""

import asyncio
import logging
from datetime import date
from typing import Set

from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.session import async_session_factory
from src.utils.telegram.parser import TelegramParser
from extended_queries import SEARCH_QUERIES_EXTENDED

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ChannelDeduplicator:
    """Дедупликатор каналов."""
    
    def __init__(self):
        self.seen_usernames: Set[str] = set()
        self.seen_telegram_ids: Set[int] = set()
        self.seen_titles: Set[str] = set()
    
    def is_duplicate(self, username: str, telegram_id: int, title: str) -> bool:
        """Проверить на дубликат."""
        username_clean = username.lower().strip() if username else ""
        title_clean = title.lower().strip() if title else ""
        
        # Проверка по username
        if username_clean and username_clean in self.seen_usernames:
            return True
        
        # Проверка по Telegram ID
        if telegram_id and telegram_id in self.seen_telegram_ids:
            return True
        
        # Проверка по title (для каналов без username)
        if title_clean and title_clean in self.seen_titles:
            return True
        
        # Добавляем в сеты
        if username_clean:
            self.seen_usernames.add(username_clean)
        if telegram_id:
            self.seen_telegram_ids.add(telegram_id)
        if title_clean:
            self.seen_titles.add(title_clean)
        
        return False


async def parse_with_deduplication(
    parser: TelegramParser,
    chat_repo: ChatAnalyticsRepository,
    deduplicator: ChannelDeduplicator,
    queries: list[str],
    max_per_query: int = 10,
) -> dict:
    """Парсинг с дедупликацией."""
    
    stats = {
        'queries_processed': 0,
        'channels_found': 0,
        'channels_added': 0,
        'channels_updated': 0,
        'duplicates_skipped': 0,
        'errors': 0,
    }
    
    for i, query in enumerate(queries):
        stats['queries_processed'] += 1
        
        try:
            # Поиск каналов
            results = await parser.search_public_chats(query, limit=max_per_query)
            
            if not results:
                logger.debug(f"Query '{query}': 0 channels found")
                continue
            
            stats['channels_found'] += len(results)
            
            # Обработка каждого канала
            for chat_info in results:
                username = chat_info.username or f"_{chat_info.telegram_id}"
                telegram_id = chat_info.telegram_id
                title = chat_info.title or ""
                
                # Проверка на дубликат
                if deduplicator.is_duplicate(username, telegram_id, title):
                    stats['duplicates_skipped'] += 1
                    logger.debug(f"Duplicate skipped: {username}")
                    continue
                
                try:
                    # Получаем или создаём чат
                    chat, is_new = await chat_repo.get_or_create_chat(username)
                    
                    # Обновляем данные
                    chat.telegram_id = telegram_id
                    chat.title = title
                    chat.description = chat_info.description
                    chat.member_count = chat_info.member_count or 0
                    chat.topic = "other"  # Будет определено позже
                    chat.is_active = True
                    chat.is_public = bool(username)
                    chat.is_verified = chat_info.is_verified
                    chat.is_scam = chat_info.is_scam
                    chat.is_fake = chat_info.is_fake
                    chat.rating = 7.0 if chat_info.is_verified else 5.0
                    chat.last_subscribers = chat_info.member_count or 0
                    chat.last_parsed_at = date.today()
                    
                    # Сохраняем meta_json
                    if chat_info.meta_json:
                        chat.language = chat_info.meta_json.get("language", "ru")
                        chat.russian_score = chat_info.meta_json.get("russian_score", 1.0)
                    else:
                        chat.language = "ru"
                        chat.russian_score = 1.0
                    
                    await chat_repo._session.flush()
                    
                    if is_new:
                        stats['channels_added'] += 1
                        logger.info(f"+ [{stats['channels_added']}] {username}: {title} ({chat_info.member_count or 0} подп.)")
                    else:
                        stats['channels_updated'] += 1
                        logger.debug(f"~ {username}: updated")
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.warning(f"Error saving {username}: {e}")
                    continue
            
            # Прогресс
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(queries)} queries, {stats['channels_added']} channels added")
            
            # Пауза между запросами
            await asyncio.sleep(2)
            
        except Exception as e:
            stats['errors'] += 1
            logger.error(f"Error processing query '{query}': {e}")
            await asyncio.sleep(5)
            continue
    
    return stats


async def main():
    """Основная функция."""
    logger.info("=" * 70)
    logger.info("МАСШТАБНЫЙ ПАРСИНГ TELEGRAM С ДЕДУПЛИКАЦИЕЙ")
    logger.info(f"Всего запросов: {len(SEARCH_QUERIES_EXTENDED)}")
    logger.info("=" * 70)
    
    async with async_session_factory() as session:
        chat_repo = ChatAnalyticsRepository(session)
        deduplicator = ChannelDeduplicator()
        
        # Загружаем существующие каналы для дедупликации
        logger.info("Загрузка существующих каналов для дедупликации...")
        existing_channels = await chat_repo.get_all_active()
        for ch in existing_channels:
            deduplicator.seen_usernames.add(ch.username.lower() if ch.username else "")
            deduplicator.seen_telegram_ids.add(ch.telegram_id)
            deduplicator.seen_titles.add(ch.title.lower() if ch.title else "")
        
        logger.info(f"Загружено {len(existing_channels)} существующих каналов")
        
        async with TelegramParser() as parser:
            logger.info("Telegram parser started")
            
            # Запуск парсинга
            stats = await parse_with_deduplication(
                parser=parser,
                chat_repo=chat_repo,
                deduplicator=deduplicator,
                queries=SEARCH_QUERIES_EXTENDED,
                max_per_query=15,
            )
            
            # Коммит
            await session.commit()
        
        # Итоги
        logger.info("\n" + "=" * 70)
        logger.info("ПАРСИНГ ЗАВЕРШЁН!")
        logger.info(f"Обработано запросов: {stats['queries_processed']}")
        logger.info(f"Найдено каналов: {stats['channels_found']}")
        logger.info(f"Добавлено: {stats['channels_added']}")
        logger.info(f"Обновлено: {stats['channels_updated']}")
        logger.info(f"Пропущено дубликатов: {stats['duplicates_skipped']}")
        logger.info(f"Ошибок: {stats['errors']}")
        logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
