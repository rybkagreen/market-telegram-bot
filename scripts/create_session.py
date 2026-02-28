"""
Скрипт для создания Telethon-сессии.
Запускать ЛОКАЛЬНО (не в Docker) — требует интерактивного ввода.

После создания сессии файл parser_session.session нужно
скопировать в Docker-контейнер.
"""
import asyncio
import sys
from pathlib import Path

# Добавить корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from telethon import TelegramClient
from src.config.settings import settings


async def main() -> None:
    print("=" * 50)
    print("Создание Telethon-сессии для парсера")
    print("=" * 50)
    print(f"\nAPI_ID: {settings.api_id}")
    print(f"API_HASH: {settings.api_hash[:8]}...\n")

    client = TelegramClient(
        session="parser_session",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
    )

    await client.start()  # запросит номер телефона и код

    me = await client.get_me()
    print(f"\n✅ Авторизован как: {me.first_name} (@{me.username})")
    print(f"Файл сессии: parser_session.session")

    # Тест — проверить что можем получить публичный канал
    print("\nТест доступа к публичному каналу...")
    try:
        entity = await client.get_entity("durov")
        print(f"✅ Тест успешен: @durov — {entity.participants_count:,} подписчиков")
    except Exception as e:
        print(f"⚠️ Тест не прошёл: {e}")

    await client.disconnect()
    print("\n✅ Сессия создана: parser_session.session")
    print("Следующий шаг: скопировать файл в Docker-контейнер")


if __name__ == "__main__":
    asyncio.run(main())
