"""
Скрипт для создания Telethon StringSession.
Запускать ЛОКАЛЬНО — требует интерактивного ввода.

После запуска скопируй строку TELETHON_SESSION_STRING в .env
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest

from src.config.settings import settings


async def main() -> None:
    print("=" * 60)
    print("Генерация Telethon StringSession")
    print("=" * 60)
    print(f"\nAPI_ID: {settings.api_id}")
    print(f"API_HASH: {settings.api_hash[:8]}...\n")

    if settings.api_id == 12345678 or not settings.api_hash:
        print("❌ API_ID и API_HASH не настроены!")
        print("Получи их на https://my.telegram.org")
        return

    # Создать клиент с пустой StringSession
    # ВАЖНО: указываем device_model чтобы Telegram не блокировал запрос кода
    # https://github.com/LonamiWebs/Telethon/issues/4730
    client = TelegramClient(
        session=StringSession(),
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        device_model='Desktop',
        system_version='Windows 10',
        app_version='3.1.1 x64',
        lang_code='en',
        system_lang_code='en-US',
    )

    print("Авторизация в Telegram...")
    print("(код придёт в приложение Telegram, не SMS)\n")

    await client.start()

    # Получить строку сессии
    session_string = client.session.save()

    me = await client.get_me()
    print(f"\n✅ Авторизован как: {me.first_name} (@{me.username})")

    # Тест
    print("\nТест доступа к публичному каналу...")
    try:
        entity = await client.get_entity("tproger")
        full = await client(GetFullChannelRequest(entity))
        subs = full.full_chat.participants_count
        print(f"✅ Тест успешен: @tproger — {subs:,} подписчиков")
    except Exception as e:
        print(f"⚠️ Тест не прошёл: {e}")

    await client.disconnect()

    print("\n" + "=" * 60)
    print("СКОПИРУЙ ЭТУ СТРОКУ В .env:")
    print("=" * 60)
    print(f"\nTELETHON_SESSION_STRING={session_string}\n")
    print("=" * 60)
    print("\n⚠️  НЕ публикуй эту строку в git!")
    print("⚠️  Она даёт полный доступ к аккаунту Telegram!")


if __name__ == "__main__":
    asyncio.run(main())
