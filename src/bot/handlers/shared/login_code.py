"""
Bot handler for /login command — generates one-time auth code for web portal login.

Flow:
1. User sends /login to bot
2. Bot generates 6-digit code, stores in Redis (TTL 5 min)
3. User enters code on web portal to get JWT
"""

import random
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.config.settings import settings as _settings

logger = logging.getLogger(__name__)

router = Router()

_CODE_TEMPLATE = (
    "🔑 *Код для входа на портал*\n\n"
    "Ваш код: `{code}`\n\n"
    "Откройте rekharbor.ru/portal → «Войти через код»\n"
    "и введите этот код.\n\n"
    "⏳ Код действует 5 минут и используется 1 раз."
)


@router.message(Command("login"))
async def cmd_login(message: Message) -> None:
    """Генерирует одноразовый код для входа через веб-портал."""
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    # Generate 6-digit code
    code = f"{random.randint(100000, 999999)}"

    # Store in Redis (TTL 5 min)
    import redis.asyncio as aioredis

    r = aioredis.from_url(str(_settings.redis_url))
    try:
        redis_key = f"login_code:{code}"
        await r.setex(redis_key, 300, str(telegram_id))  # 5 min TTL
        logger.info(f"Generated login code {code} for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"Redis error generating login code: {e}")
        await message.answer(
            "❌ Ошибка генерации кода. Попробуйте позже или войдите через кнопку Telegram Login.",
            parse_mode="Markdown",
        )
        return
    finally:
        await r.aclose()  # type: ignore[attr-defined]

    await message.answer(
        _CODE_TEMPLATE.format(code=code),
        parse_mode="Markdown",
    )
