"""
Сервис для автоматической классификации каналов по категориям.
Использует Mistral AI API.
"""

import logging
from typing import TypedDict

from src.core.services.mistral_ai_service import mistral_ai_service

logger = logging.getLogger(__name__)


class CategoryResult(TypedDict):
    topic: str
    subcategory: str
    confidence: float


async def classify_channel(title: str, description: str) -> CategoryResult:
    """
    Классифицировать канал по названию и описанию.

    Args:
        title: Название канала.
        description: Описание канала.

    Returns:
        Результат классификации.
    """
    result = await mistral_ai_service.classify_channel(
        title=title,
        description=description or "",
    )

    return CategoryResult(
        topic=result.topic,
        subcategory=result.subcategory or "",
        confidence=result.confidence,
    )
