#!/usr/bin/env python3
"""
Авторизация Telethon через QR-код в терминале.

Запуск на сервере (не в контейнере):
    cd /opt/market-telegram-bot
    PYTHONPATH=/opt/market-telegram-bot .venv/bin/python3 scripts/telethon_auth.py

Как сканировать QR:
    Телефон → Telegram → Настройки → Устройства → Подключить устройство
"""

import asyncio
import os
import sys

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_qr_ascii(url: str):
    """Вывести QR-код в терминал через встроенный ASCII-метод qrcode."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    print("\n" + "=" * 60)
    print("  📱 КАК СКАНИРОВАТЬ:")
    print("  Telegram (телефон) → Настройки → Устройства")
    print("  → Подключить устройство → наведите камеру")
    print("=" * 60 + "\n")

    # Встроенный метод qrcode для терминала — самый надёжный
    qr.print_ascii(invert=True)

    print("\n" + "=" * 60)
    print("  Ожидание сканирования... (Ctrl+C для отмены)")
    print("=" * 60 + "\n")


async def main():
    from src.config.settings import settings

    api_id = (
        getattr(settings, "api_id", None)
        or getattr(settings, "telegram_api_id", None)
        or int(os.getenv("TELEGRAM_API_ID", 0))
    )

    api_hash = (
        getattr(settings, "api_hash", None)
        or getattr(settings, "telegram_api_hash", None)
        or os.getenv("TELEGRAM_API_HASH", "")
    )

    telethon_session = getattr(settings, "telethon_session_string", None) or os.getenv(
        "TELETHON_SESSION_STRING", ""
    )

    if not api_id or not api_hash:
        print("❌ Не найдены TELEGRAM_API_ID / TELEGRAM_API_HASH в settings или .env")
        return

    print(f"\nAPI_ID: {api_id}")
    print(f"API_HASH: {api_hash[:6]}...")
    print(
        f"TELETHON_SESSION: {telethon_session[:50] if telethon_session else '❌ Не найдена'}...\n"
    )

    # Проверить существующую сессию если есть
    if telethon_session:
        print("🔄 Проверка существующей сессии...\n")
        client = TelegramClient(
            StringSession(telethon_session),
            api_id,
            api_hash,
            device_model="Linux Server",
            system_version="Ubuntu 22.04",
            app_version="1.0",
            lang_code="ru",
        )

        await client.connect()

        if await client.is_user_authorized():
            print("✅ Сессия действительна!")
            _save_session(client)
            await client.disconnect()
            return
        else:
            print("❌ Сессия недействительна, требуется новая авторизация\n")
            await client.disconnect()

    # Новая авторизация через QR
    print("🔄 Запуск QR-авторизации...\n")
    client = TelegramClient(
        StringSession(),
        api_id,
        api_hash,
        device_model="Linux Server",
        system_version="Ubuntu 22.04",
        app_version="1.0",
        lang_code="ru",
    )

    await client.connect()

    # --- QR-авторизация ---
    print("🔄 Запуск QR-авторизации...\n")

    while True:
        qr_login = await client.qr_login()
        print_qr_ascii(qr_login.url)

        try:
            await qr_login.wait(timeout=30)
            break  # Успех

        except TimeoutError:
            print("⏱ QR истёк, генерирую новый...\n")
            continue  # qr_login.recreate() вызывается автоматически через новый qr_login()

        except SessionPasswordNeededError:
            print("\n🔐 Включена двухфакторная аутентификация (2FA)")
            password = input("Введите пароль 2FA: ").strip()
            await client.sign_in(password=password)
            break

        except Exception as e:
            print(f"\n❌ Ошибка: {type(e).__name__}: {e}")
            await client.disconnect()
            return

    # Успешная авторизация
    me = await client.get_me()
    print("\n✅ АВТОРИЗАЦИЯ УСПЕШНА!")
    print(f"   Аккаунт: {me.first_name} {me.last_name or ''} (@{me.username or 'без username'})")
    print(f"   ID: {me.id}\n")

    _save_session(client)
    await client.disconnect()


def _save_session(client: TelegramClient):
    session_string = client.session.save()

    print("=" * 60)
    print("СКОПИРУЙТЕ СТРОКУ НИЖЕ В .env:")
    print("=" * 60)
    print(f"\nTELETHON_SESSION_STRING={session_string}\n")
    print("=" * 60)
    print("\n📋 Затем:")
    print("   1. Вставьте строку в .env (замените старое значение)")
    print("   2. docker compose restart bot")
    print("=" * 60 + "\n")

    # Дополнительно сохранить в файл
    output_file = "telethon_session.txt"
    with open(output_file, "w") as f:
        f.write(f"TELETHON_SESSION_STRING={session_string}\n")
    print(f"💾 Сессия также сохранена в файл: {output_file}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⛔ Прервано")
    except Exception as e:
        print(f"\n❌ {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
