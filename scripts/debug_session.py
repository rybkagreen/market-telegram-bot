"""
Отладочный скрипт создания Telethon StringSession.
Добавлено детальное логирование для диагностики проблем с кодом авторизации.
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Включить максимальное логирование Telethon
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("session_debug.log", encoding="utf-8"),
    ]
)

# Логи Telethon — показывают все сетевые запросы
logging.getLogger("telethon").setLevel(logging.DEBUG)
logging.getLogger("telethon.network").setLevel(logging.DEBUG)
logging.getLogger("telethon.client").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneNumberInvalidError,
    PhoneNumberBannedError,
    PhoneNumberFloodError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    FloodWaitError,
)
from src.config.settings import settings


async def main() -> None:
    print("\n" + "=" * 60)
    print("Отладочное создание Telethon StringSession")
    print("=" * 60)
    print(f"API_ID: {settings.api_id}")
    print(f"API_HASH: {settings.api_hash[:8]}...")
    print(f"Лог сохраняется в: session_debug.log")
    print("=" * 60 + "\n")

    # Создать клиент с пустой StringSession
    client = TelegramClient(
        session=StringSession(),
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        # Параметры для стабильного подключения
        connection_retries=5,
        retry_delay=2,
        timeout=30,
    )

    print("Подключение к Telegram серверам...")
    logger.debug("Начало подключения к Telegram")

    await client.connect()

    # Проверить успешность подключения
    is_connected = client.is_connected()
    print(f"Подключение: {'✅ успешно' if is_connected else '❌ неуспешно'}")
    logger.debug(f"Статус подключения: {is_connected}")

    if not is_connected:
        print("❌ Не удалось подключиться к Telegram. Проверь интернет-соединение.")
        return

    # Проверить уже авторизован ли клиент
    is_authorized = await client.is_user_authorized()
    print(f"Уже авторизован: {'✅ да' if is_authorized else 'нет'}")

    if is_authorized:
        me = await client.get_me()
        print(f"\n✅ Уже авторизован как: {me.first_name} (@{me.username})")
        session_string = client.session.save()
        print("\n" + "=" * 60)
        print("СТРОКА СЕССИИ (скопируй в .env):")
        print("=" * 60)
        print(f"\nTELETHON_SESSION_STRING={session_string}\n")
        await client.disconnect()
        return

    # Запросить номер телефона
    print("\n" + "=" * 60)
    print("ВВОД НОМЕРА ТЕЛЕФОНА")
    print("=" * 60)
    print("Формат: +7XXXXXXXXXX (например: +79685418800)")
    print("Можно также: 79685418800 или +7 968 541 8800")
    print("Telethon сам нормализует номер")
    print("=" * 60)
    
    phone = input("\nВведи номер телефона: ").strip()
    
    # Нормализация номера
    phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    
    print(f"\nНормализованный номер: {phone}")
    print(f"\nЗапрашиваю код для номера {phone}...")
    print("⚠️  Код придёт в ПРИЛОЖЕНИЕ Telegram (не SMS)!")
    print("👉 Открой Telegram → найди диалог с 'Telegram' (сервисный аккаунт)")
    print("   Сообщение: 'Login code: XXXXX. Do not give this code...'")
    
    logger.debug(f"Отправка кода на номер: {phone}")

    try:
        # Явно указываем force_sms=False — код ТОЛЬКО в приложение Telegram
        result = await client.send_code_request(phone, force_sms=False)

        logger.debug(f"Ответ send_code_request: {result}")
        logger.debug(f"phone_code_hash: {result.phone_code_hash[:8]}...")
        logger.debug(f"type: {result.type}")
        logger.debug(f"next_type: {result.next_type}")

        print(f"\n✅ Запрос кода отправлен успешно!")
        print(f"   Тип доставки: {result.type.__class__.__name__}")
        
        # Расшифровка типа доставки
        from telethon.tl.types import SentCodeTypeApp, SentCodeTypeSms, SentCodeTypeCall
        if isinstance(result.type, SentCodeTypeApp):
            print(f"   📱 Код отправлен в ПРИЛОЖЕНИЕ Telegram")
            print(f"   👉 Открой Telegram → ЧАТЫ → найди 'Telegram' (синяя галочка)")
            print(f"   👉 Или: Настройки → Устройства → Запросы на вход")
        elif isinstance(result.type, SentCodeTypeSms):
            print(f"   📳 Код отправлен по SMS (редко бывает)")
        elif isinstance(result.type, SentCodeTypeCall):
            print(f"   📞 Код будет продиктован голосовым звонком")
        
        if result.next_type:
            print(f"   Если код не пришёл, следующий способ: {result.next_type.__class__.__name__}")
        
        print(f"\n🔍 ГДЕ ИСКАТЬ КОД:")
        print(f"   1. Открой Telegram (мобильное или десктоп)")
        print(f"   2. Посмотри в ЧАТАХ — диалог 'Telegram' с синей галочкой")
        print(f"   3. Если нет — Настройки → Приватность → Запросы на вход")
        print(f"   4. Проверь АРХИВ чатов")
        print(f"\n   Сообщение выглядит так:")
        print(f"   ┌─────────────────────────────────────")
        print(f"   │ Telegram [синяя галочка]")
        print(f"   │ Login code: 12345")
        print(f"   │ Do not give this code to anyone...")
        print(f"   └─────────────────────────────────────")

    except PhoneNumberInvalidError:
        print(f"❌ Номер {phone} невалидный. Проверь формат (+7XXXXXXXXXX)")
        await client.disconnect()
        return
    except PhoneNumberBannedError:
        print(f"❌ Номер {phone} заблокирован в Telegram")
        await client.disconnect()
        return
    except PhoneNumberFloodError:
        print(f"❌ Слишком много запросов с этого номера. Подожди час и попробуй снова.")
        await client.disconnect()
        return
    except FloodWaitError as e:
        print(f"❌ FloodWait: нужно подождать {e.seconds} секунд ({e.seconds // 60} мин)")
        await client.disconnect()
        return
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при send_code_request: {e}")
        print(f"❌ Ошибка: {type(e).__name__}: {e}")
        print(f"   Подробности в файле: session_debug.log")
        await client.disconnect()
        return

    # Ввести код
    code = input("\nВведи код из Telegram: ").strip().replace(" ", "")
    logger.debug(f"Введён код длиной {len(code)} символов")

    try:
        await client.sign_in(phone, code)
        print("✅ Авторизация успешна!")

    except PhoneCodeInvalidError:
        print("❌ Неверный код. Попробуй запустить скрипт заново.")
        await client.disconnect()
        return
    except PhoneCodeExpiredError:
        print("❌ Код устарел (действует 5 минут). Запусти скрипт заново.")
        await client.disconnect()
        return
    except SessionPasswordNeededError:
        # Двухфакторная авторизация
        print("\n🔐 Включена двухфакторная авторизация (2FA)")
        password = input("Введи пароль 2FA: ").strip()
        try:
            await client.sign_in(password=password)
            print("✅ 2FA авторизация успешна!")
        except Exception as e:
            print(f"❌ Неверный пароль 2FA: {e}")
            await client.disconnect()
            return
    except Exception as e:
        logger.exception(f"Ошибка при sign_in: {e}")
        print(f"❌ Ошибка входа: {type(e).__name__}: {e}")
        await client.disconnect()
        return

    # Получить строку сессии
    me = await client.get_me()
    session_string = client.session.save()

    print(f"\n✅ Авторизован как: {me.first_name} (@{me.username})")

    # Тест доступа
    print("\nТест доступа к публичному каналу @tproger...")
    try:
        from telethon.tl.functions.channels import GetFullChannelRequest
        entity = await client.get_entity("tproger")
        full = await client(GetFullChannelRequest(entity))
        subs = full.full_chat.participants_count
        print(f"✅ Тест успешен: @tproger — {subs:,} подписчиков")
    except Exception as e:
        print(f"⚠️ Тест не прошёл: {e}")
        logger.exception("Ошибка теста доступа")

    await client.disconnect()

    # Вывести строку сессии
    print("\n" + "=" * 60)
    print("СКОПИРУЙ ЭТУ СТРОКУ В .env:")
    print("=" * 60)
    print(f"\nTELETHON_SESSION_STRING={session_string}\n")
    print("=" * 60)
    print("\n⚠️  НЕ публикуй эту строку в git!")
    print("⚠️  Она даёт полный доступ к аккаунту Telegram!")
    print(f"\nДетальный лог сохранён в: session_debug.log")


if __name__ == "__main__":
    asyncio.run(main())
