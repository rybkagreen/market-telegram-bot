"""
Parser Singleton — глобальный экземпляр Telethon парсера.

Используется в handlers для получения subscriber count каналов.
"""

import logging

from src.utils.telegram.parser import TelegramParser

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# Parser Singleton — глобальный экземпляр Telethon парсера
# ══════════════════════════════════════════════════════════════
_parser: TelegramParser | None = None


def get_parser() -> TelegramParser:
    """
    Получить глобальный экземпляр TelegramParser.

    Returns:
        TelegramParser: Единственный экземпляр парсера.

    Raises:
        RuntimeError: Если парсер не инициализирован.
    """
    if _parser is None:
        raise RuntimeError(
            "TelegramParser not initialized. "
            "Call init_parser() before using get_parser()."
        )
    return _parser


async def init_parser() -> TelegramParser:
    """
    Инициализировать глобальный парсер.

    Returns:
        TelegramParser: Инициализированный парсер.
    """
    global _parser
    if _parser is not None:
        return _parser

    _parser = TelegramParser()
    await _parser.start()
    logger.info("TelegramParser initialized as singleton")
    return _parser


async def shutdown_parser() -> None:
    """
    Остановить глобальный парсер.
    """
    global _parser
    if _parser is not None:
        await _parser.stop()
        _parser = None
        logger.info("TelegramParser stopped")
