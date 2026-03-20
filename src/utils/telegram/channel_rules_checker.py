"""
Проверка правил канала на запрет рекламы.
Используется в parser_tasks.py при парсинге новых каналов
и при периодическом обновлении через Celery Beat.

Также используется для проверки каналов при добавлении через Mini App.
"""

import logging
import re
from dataclasses import dataclass

from telegram import Chat

logger = logging.getLogger(__name__)

# Паттерны запрета рекламы в описании/правилах канала
_NO_ADS_PATTERNS: list[str] = [
    r"реклам[аы]?\s*(запрещен[ао]?|не\s*допуска|не\s*принима|нет|без)",
    r"без\s*рекла[мы]",
    r"no\s*(ads?|advertising|sponsored|spam)",
    r"реклам[аы]?\s*нет",
    r"не\s*присылайте\s*реклам",
    r"спам\s*запрещ[её]н",
    r"only\s*official\s*(posts?|content)",
    r"рекламодател[яьи]\s*—?\s*нет",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _NO_ADS_PATTERNS]

# Запрещённые ключевые слова (казино, ставки, 18+, порно, насилие, наркотики, оружие, мошенничество)
FORBIDDEN_KEYWORDS: list[str] = [
    "казино",
    "ставки",
    "беттинг",
    "18+",
    "порно",
    "секс",
    "насилие",
    "наркотики",
    "нарк",
    "оружие",
    "мошенничество",
    "скам",
    "развод",
    "пирамида",
    "террор",
    "экстремизм",
    "азартные игры",
    "слоты",
    "букмекер",
]

# Минимальное количество подписчиков для канала
MIN_SUBSCRIBERS = 100


@dataclass
class ChannelRulesResult:
    allows_ads: bool  # True = реклама разрешена (или правила не найдены)
    reject_reason: str = ""  # причина отказа
    checked_text: str = ""  # текст который проверялся (для лога, обрезан до 500 символов)


async def check_channel_rules(client, chat_username: str) -> ChannelRulesResult:
    """
    Проверить описание канала на запрет рекламы через Telethon-клиент.

    При любой ошибке возвращает allows_ads=True (не блокируем по умолчанию).

    Args:
        client: Telethon TelegramClient.
        chat_username: Username канала (без @).

    Returns:
        ChannelRulesResult с результатом проверки.
    """
    try:
        entity = await client.get_entity(chat_username)
        full = await client.get_full_channel(entity)
        about: str = getattr(full.full_chat, "about", "") or ""
        checked_text = about[:500]

        for pattern in COMPILED_PATTERNS:
            if pattern.search(about):
                return ChannelRulesResult(
                    allows_ads=False,
                    reject_reason=f"no-ads rule in description (pattern: {pattern.pattern[:50]})",
                    checked_text=checked_text,
                )

        return ChannelRulesResult(allows_ads=True, checked_text=checked_text)

    except Exception as e:
        logger.debug(f"Could not check rules for {chat_username}: {e}")
        # Ошибка доступа — не блокируем, просто пропускаем проверку
        return ChannelRulesResult(allows_ads=True, reject_reason=f"check_failed: {e}")


class ChannelRulesChecker:
    """
    Класс для проверки канала на соответствие правилам платформы.

    Проверки:
    - Минимальное количество подписчиков (100+)
    - Запрещённые ключевые слова в описании
    - Тип чата (должен быть канал)
    - Публичность канала (есть username)
    """

    FORBIDDEN_KEYWORDS = FORBIDDEN_KEYWORDS
    MIN_SUBSCRIBERS = MIN_SUBSCRIBERS

    @classmethod
    async def check_channel(
        cls,
        chat: Chat,
        is_admin: bool = False,
    ) -> tuple[bool, list[str], list[str]]:
        """
        Проверить канал на соответствие правилам платформы.

        Args:
            chat: Telegram Chat объект из Bot API.
            is_admin: Если True — пропускать проверку MIN_SUBSCRIBERS (для админов).

        Returns:
            Кортеж (valid, violations, warnings):
            - valid: True если канал соответствует всем правилам
            - violations: Список нарушений (пустой если valid=True)
            - warnings: Список предупреждений (для админов при нарушении MIN_SUBSCRIBERS)
        """
        violations: list[str] = []
        warnings: list[str] = []

        # 1. Проверка типа канала (должен быть channel)
        if chat.type != "channel":
            violations.append(f"Неверный тип чата: {chat.type} (требуется channel)")

        # 2. Проверка публичности (должен быть username)
        if not chat.username:
            violations.append("Канал должен быть публичным (требуется username)")

        # 3. Проверка минимального количества подписчиков
        member_count = 0
        try:
            if hasattr(chat, "get_member_count"):
                member_count = await chat.get_member_count()
            elif hasattr(chat, "member_count"):
                member_count = chat.member_count or 0
        except Exception:
            logger.warning(f"Cannot get member count for {chat.username}")

        if member_count < cls.MIN_SUBSCRIBERS:
            if is_admin:
                # Для админов — только предупреждение (тестовый канал)
                warnings.append(f"Тестовый канал ({member_count} подписчиков, мин. {cls.MIN_SUBSCRIBERS})")
            else:
                # Для обычных пользователей — блокирующее нарушение
                violations.append(f"Минимум {cls.MIN_SUBSCRIBERS} подписчиков (сейчас: {member_count})")

        # 4. Проверка описания на запрещённые слова
        description = getattr(chat, "description", "") or ""
        description_lower = description.lower()

        for keyword in cls.FORBIDDEN_KEYWORDS:
            if keyword.lower() in description_lower:
                violations.append(f"Запрещённый контент в описании: '{keyword}'")
                break  # Достаточно одного нарушения

        return len(violations) == 0, violations, warnings
