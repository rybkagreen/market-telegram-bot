#!/usr/bin/env python3
"""
Импорт каналов из списка username.
"""

import asyncio
import logging
from datetime import UTC, date

from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.session import async_session_factory
from src.utils.telegram.parser import TelegramParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список популярных русскоязычных каналов по категориям
CHANNELS = {
    "business": [
        "rb_ru", "vc_ru", "roem_ru", "incru", "rbcdaily", "forbes_ru",
        "vedomosti", "kommersant", "tass_agency", "ria_ru",
    ],
    "it": [
        "pythonru", "golang_ru", "javascript_ru", "frontend_ru", "devops_ru",
        "linux_ru", "docker_ru", "kubernetes_ru", "git_ru", "code_review",
    ],
    "marketing": [
        "marketing_ru", "smm_ru", "targetolog", "context_ru", "seo_ru",
        "content_marketing", "brand_ru", "pr_ru",
    ],
    "news": [
        "rian_ru", "tass_agency", "interfax_ru", "lenta_ru", "gazeta_ru",
        "meduza", "holodmedia", "verstka",
    ],
    "education": [
        "geekbrains", "skillbox", "netology", "yandex_praktikum", "stepik",
        "openedu_ru", "postnauka", "arithmocracy",
    ],
    "crypto": [
        "cryptonews_ru", "bitcoin_ru", "ethereum_ru", "defi_ru", "nft_ru",
        "web3_ru", "blockchain_ru",
    ],
    "health": [
        "zdorovie_ru", "fitness_ru", "sport_ru", "yoga_ru", "running_ru",
    ],
    "lifestyle": [
        "travel_ru", "food_ru", "fashion_ru", "design_ru", "art_ru",
        "cinema_ru", "music_ru", "books_ru",
    ],
}


async def import_channels():
    """Импорт каналов из списка."""
    logger.info("=" * 60)
    logger.info("ИМПОРТ КАНАЛОВ ИЗ СПИСКА")
    logger.info("=" * 60)
    
    async with async_session_factory() as session:
        chat_repo = ChatAnalyticsRepository(session)
        
        async with TelegramParser() as parser:
            total = 0
            success = 0
            
            for topic, usernames in CHANNELS.items():
                logger.info(f"\nКатегория: {topic} ({len(usernames)} каналов)")
                
                for username in usernames:
                    total += 1
                    try:
                        # Проверяем канал
                        details = await parser.resolve_and_validate(username)
                        
                        if details:
                            chat, is_new = await chat_repo.get_or_create_chat(username)
                            
                            # Обновляем данные
                            chat.telegram_id = details.telegram_id
                            chat.title = details.title
                            chat.description = details.description
                            chat.member_count = details.member_count or 0
                            chat.topic = topic
                            chat.is_active = details.is_active
                            chat.is_public = bool(details.username)
                            chat.can_post = not details.is_broadcast
                            chat.rating = details.rating or 5.0
                            chat.last_subscribers = details.member_count or 0
                            chat.last_parsed_at = date.today()
                            
                            await chat_repo._session.flush()
                            
                            if is_new:
                                logger.info(f"  + @{username}: {details.title} ({details.member_count or 0} подп.)")
                                success += 1
                            else:
                                logger.info(f"  ~ @{username}: обновлён")
                        else:
                            logger.warning(f"  ✗ @{username}: не найден или приватный")
                            
                    except Exception as e:
                        logger.warning(f"  ✗ @{username}: {e}")
                    
                    # Пауза между запросами
                    await asyncio.sleep(1.5)
        
        # Коммит
        await session.commit()
        
    logger.info("\n" + "=" * 60)
    logger.info(f"ГОТОВО! Проверено: {total}, Добавлено: {success}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(import_channels())
