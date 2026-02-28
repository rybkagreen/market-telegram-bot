"""
Скрипт для загрузки начального списка Telegram чатов в БД.
Запускать ПОСЛЕ создания сессии.

Источники чатов:
1. Список из TGStat по тематикам (если TGStatParser работает)
2. Ручной список популярных русскоязычных каналов
3. Поиск через Telethon по ключевым словам
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.db.session import async_session_factory
from src.db.repositories.chat_analytics import ChatAnalyticsRepository


# ─── Начальный список чатов по тематикам ───────────────────────────────────
# Добавь каналы которые релевантны для твоей платформы
SEED_CHATS: dict[str, list[str]] = {
    "IT": [
        "python_ru",
        "tproger",
        "Pythonist",
        "django_pythonist",
        "devops_ru",
        "linux_ru_academy",
        "data_analysis_ml",
        "machinelearning_ru",
        "AIMLgroup",
        "neural_network_ru",
    ],
    "Бизнес": [
        "businessru",
        "rusbase",
        "startupoftheday",
        "retail_ru",
        "marketingpro_ru",
        "digitalagency_ru",
    ],
    "Новости": [
        "breakingmash",
        "russica2",
        "meduzaio",
        "rbc_news",
        "lentaru",
    ],
    "Крипта": [
        "forklog",
        "cryptoru",
        "coinmarketru",
        "bitcointalk_ru",
    ],
    "Курсы": [
        "stepik_courses",
        "netologyru",
        "skillboxru",
        "geekbrains_official",
    ],
    "Услуги": [
        "freelancehunt_ru",
        "fl_ru",
        "kwork_ru",
    ],
    "Товары": [
        "ozon_official",
        "wildberries_official",
        "avito_ru",
    ],
}


async def seed_chats() -> None:
    total_added = 0
    total_existing = 0

    async with async_session_factory() as session:
        repo = ChatAnalyticsRepository(session)

        for topic, usernames in SEED_CHATS.items():
            print(f"\nTopic: {topic} ({len(usernames)} chats)")
            for username in usernames:
                chat, is_new = await repo.get_or_create_chat(username)
                if is_new:
                    # Установить тематику
                    chat.topic = topic
                    await session.flush()
                    total_added += 1
                    print(f"  + Added: @{username}")
                else:
                    total_existing += 1
                    print(f"  - Exists: @{username}")

        await session.commit()

    print(f"\n{'='*50}")
    print(f"Added new: {total_added}")
    print(f"Already existed: {total_existing}")
    print(f"Total in list: {total_added + total_existing}")
    print(f"\nChats ready for parsing. Run parser:")
    print("docker compose exec worker celery -A src.tasks.celery_app call \\")
    print("    tasks.parser_tasks:collect_all_chats_stats")


if __name__ == "__main__":
    asyncio.run(seed_chats())
