"""
Проверка правил канала на запрет рекламы.
Используется в parser_tasks.py при парсинге новых каналов
и при периодическом обновлении через Celery Beat.
"""

import logging
import re
from dataclasses import dataclass

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
