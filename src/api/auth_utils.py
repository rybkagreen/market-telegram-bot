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
from typing import Literal
from urllib.parse import parse_qsl, unquote

import jwt as pyjwt

from src.config.settings import settings

logger = logging.getLogger(__name__)

JwtSource = Literal["mini_app", "web_portal"]


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


def create_jwt_token(
    user_id: int,
    telegram_id: int,
    plan: str,
    source: JwtSource,
) -> str:
    """
    Создать JWT токен с явной audience-меткой.

    Args:
        user_id: ID пользователя в БД (users.id).
        telegram_id: Telegram ID пользователя.
        plan: текущий тариф ("free", "starter", "pro", "business").
        source: каким каналом выпущен токен — `"mini_app"` или `"web_portal"`.
            Записывается в claim `aud`. Валидируется при decode.

    Returns:
        Подписанный JWT токен (строка).
    """
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(user_id),
        "tg": telegram_id,
        "plan": plan,
        "aud": source,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_jwt_token(
    token: str,
    audience: JwtSource | list[JwtSource] | None,
) -> dict:
    """
    Декодировать и проверить JWT токен.

    Args:
        token: JWT токен из заголовка Authorization.
        audience: ожидаемое значение claim `aud`.
            - конкретное значение (`"mini_app"` / `"web_portal"`) —
              разрешён только этот источник;
            - список значений — разрешён любой из перечисленных;
            - `None` — явный opt-out (audit/legacy helpers, читающие
              payload без проверки источника). Default НЕ задан намеренно:
              каждый caller обязан явно решить, что он принимает.

    Returns:
        Payload токена с полями sub, tg, plan, aud.

    Raises:
        jwt.ExpiredSignatureError: токен истёк.
        jwt.InvalidAudienceError: aud в токене есть, но не соответствует.
        jwt.MissingRequiredClaimError: aud отсутствует, а audience задан.
        jwt.InvalidTokenError: иная причина невалидности.
    """
    return pyjwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        audience=audience,
    )


# ─── Telegram Login Widget валидация ──────────────────────────


def validate_telegram_login_widget(data: dict) -> dict:
    """
    Проверить подпись данных от Telegram Login Widget.

    Алгоритм (официальная документация):
    https://core.telegram.org/widgets/login#checking-authorization

    1. Извлечь hash из данных
    2. Отсортировать остальные поля по ключу
    3. Соединить в формате key=value через \n
    4. secret_key = SHA256(bot_token)
    5. hmac = HMAC-SHA256(secret_key, data_check_string).hexdigest()
    6. Сравнить с hash (constant-time)
    7. Проверить что auth_date < 24h

    Args:
        data: dict с полями {id, auth_date, hash, first_name?, username?, photo_url?}

    Returns:
        dict с данными пользователя (telegram_id, first_name, username и т.д.)

    Raises:
        ValueError: если подпись невалидна или данные устарели (> 24 часа)
    """
    received_hash = data.get("hash")
    if not received_hash:
        raise ValueError("Missing hash in login widget data")

    # Формируем строку для проверки без hash (ключи отсортированы)
    check_data = {k: v for k, v in data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(check_data.items()))

    # Секретный ключ = SHA256(bot_token) — НЕ HMAC с "WebAppData"!
    secret_key = hashlib.sha256(settings.bot_token.encode()).digest()

    # Вычисляем подпись
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Сравниваем (constant-time)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid login widget signature")

    # Проверяем свежесть (не старше 24 часов для Login Widget)
    auth_date = int(data.get("auth_date", 0))
    age_seconds = int(datetime.now(UTC).timestamp()) - auth_date
    if age_seconds > 86400:
        raise ValueError(f"Login widget data expired ({age_seconds}s old)")

    return {
        "telegram_id": int(data["id"]),
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name"),
        "username": data.get("username"),
        "photo_url": data.get("photo_url"),
        "auth_date": auth_date,
    }
