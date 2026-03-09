"""
Сервис для автоматической классификации каналов по категориям.
Использует LLM для анализа описания канала.
"""

import json
import logging
from typing import TypedDict

from src.core.services.ai_service import AIService

logger = logging.getLogger(__name__)


# Глобальный экземпляр AI сервиса
ai_service = AIService()


class CategoryResult(TypedDict):
    topic: str
    subcategory: str
    confidence: float


CATEGORY_PROMPT = """
Проанализируй описание Telegram канала и определи категорию и подкатегорию.

Доступные категории и подкатегории:
- бизнес: startup, small_business, personal_finance, real_estate, franchise
- ит: programming, web_dev, mobile_dev, gamedev, devops, ai_ml, data, security
- маркетинг: smm, digital, seo, content, target_ads, sales
- новости: media, politics, economy, society, world
- образование: university, online_courses, languages, professional, kids
- финансы: investments, stock_market, banking, insurance
- крипто: trading, defi, nft, bitcoin
- здоровье: medicine, fitness, nutrition, psychology
- другое: entertainment, hobbies, lifestyle, media, crypto

Описание канала: {description}

Название канала: {title}

Верни ответ ТОЛЬКО в формате JSON:
{{
    "topic": "категория",
    "subcategory": "подкатегория",
    "confidence": 0.95
}}
"""


async def classify_channel(title: str, description: str) -> CategoryResult:
    """
    Классифицировать канал по названию и описанию.

    Args:
        title: Название канала.
        description: Описание канала.

    Returns:
        Результат классификации.
    """
    prompt = CATEGORY_PROMPT.format(
        title=title[:200],  # Ограничиваем длину
        description=description[:500] if description else "Нет описания",
    )

    try:
        # Используем generate() с системным промптом для классификации
        system_prompt = "Ты — эксперт по классификации Telegram каналов. Твоя задача — точно определять категорию и подкатегорию канала на основе его названия и описания. Отвечай ТОЛЬКО в формате JSON."
        
        response = await ai_service.generate(
            prompt=prompt,
            system=system_prompt,
            use_cache=False,  # Не кэшировать классификации
        )

        # Парсим JSON ответ
        # Очищаем ответ от markdown кода если есть
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        result = json.loads(response)

        return CategoryResult(
            topic=result.get("topic", "другое"),
            subcategory=result.get("subcategory", ""),
            confidence=float(result.get("confidence", 0.5)),
        )

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse classification response: {e}")
        return CategoryResult(topic="другое", subcategory="", confidence=0.0)
    except Exception as e:
        logger.error(f"Error during classification: {e}")
        return CategoryResult(topic="другое", subcategory="", confidence=0.0)
