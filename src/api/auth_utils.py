"""
Утилиты аутентификации для Telegram Mini App.

Документация Telegram по валидации initData:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, unquote

import jwt as pyjwt

from src.config.settings import settings

logger = logging.getLogger(__name__)


# ─── Telegram initData валидация ────────────────────────────────


def validate_telegram_init_data(init_data: str) -> dict:
    """
    Проверить подпись Telegram initData и извлечь данные пользователя.

    Алгоритм (официальная документация Telegram):
    1. Распарсить init_data как URL query string
    2. Извлечь hash, убрать его из данных
    3. Отсортировать остальные поля и соединить через \n
    4. Ключ = HMAC-SHA256("WebAppData", BOT_TOKEN)
    5. Подпись = HMAC-SHA256(key, data_check_string)
    6. Сравнить подпись с hash

    Args:
        init_data: строка initData из window.Telegram.WebApp.initData

    Returns:
        dict с данными пользователя (поле 'user' содержит telegram_id, username и т.д.)

    Raises:
        ValueError: если подпись невалидна или данные устарели (> 1 часа)
    """
    # Парсим query string
    params = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash in initData")

    # Формируем строку для проверки (ключи отсортированы)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    # Вычисляем секретный ключ
    secret_key = hmac.new(
        b"WebAppData",
        settings.bot_token.encode(),
        hashlib.sha256,
    ).digest()

    # Вычисляем подпись
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Сравниваем (константное время для защиты от timing attacks)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid initData signature")

    # Проверяем свежесть данных (не старше 1 часа)
    auth_date = int(params.get("auth_date", 0))
    age_seconds = datetime.now(UTC).timestamp() - auth_date
    if age_seconds > 3600:
        raise ValueError(f"initData expired ({age_seconds:.0f}s old)")

    # Парсим user JSON
    user_json = params.get("user", "{}")
    try:
        user_data = json.loads(unquote(user_json))
    except json.JSONDecodeError as e:
        raise ValueError("Invalid user JSON in initData") from e

    return {
        "user": user_data,
        "auth_date": auth_date,
        "query_id": params.get("query_id"),
    }


# ─── JWT ────────────────────────────────────────────────────────


def create_jwt_token(user_id: int, telegram_id: int, plan: str) -> str:
    """
    Создать JWT токен для пользователя Mini App.

    Args:
        user_id: ID пользователя в БД (users.id)
        telegram_id: Telegram ID пользователя
        plan: текущий тариф ("free", "starter", "pro", "business")

    Returns:
        Подписанный JWT токен (строка)
    """
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(user_id),
        "tg": telegram_id,
        "plan": plan,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_jwt_token(token: str) -> dict:
    """
    Декодировать и проверить JWT токен.

    Args:
        token: JWT токен из заголовка Authorization

    Returns:
        Payload токена с полями sub, tg, plan

    Raises:
        jwt.ExpiredSignatureError: токен истёк
        jwt.InvalidTokenError: невалидный токен
    """
    return pyjwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
