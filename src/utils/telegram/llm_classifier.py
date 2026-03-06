"""
LLM-классификатор Telegram-каналов через Qwen (OpenRouter API).
Оптимизирован для русского языка и работы с Celery workers.
"""
import json
import logging
from dataclasses import dataclass

from src.utils.telegram.llm_classifier_prompt import (
    CATEGORIES_FOR_PROMPT,
    CLASSIFICATION_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)

# Максимум символов из постов — ограничиваем чтобы не раздувать контекст
MAX_POSTS_CHARS = 1500
MAX_DESCRIPTION_CHARS = 500


@dataclass
class ClassificationResult:
    topic: str
    subcategory: str
    confidence: float        # 0.0–1.0
    rating: float            # 1.0–10.0
    reasoning: str
    used_fallback: bool = False  # True = LLM упал, использована старая классификация


async def classify_channel_with_llm(
    ai_service,              # передавай существующий инстанс ai_service
    title: str,
    username: str,
    member_count: int,
    language: str,
    description: str,
    posts: list[str],        # список текстов последних постов
) -> ClassificationResult:
    """
    Классифицировать канал через LLM (Qwen).
    При любой ошибке возвращает fallback-результат, не бросает исключение.
    """
    # Используем Qwen сервис напрямую
    from src.core.services.qwen_ai_service import qwen_ai_service
    
    try:
        # Подготовка данных
        description_trimmed = (description or "")[:MAX_DESCRIPTION_CHARS]

        posts_text = ""
        if posts:
            combined = "\n---\n".join(p[:300] for p in posts[:5])  # макс 5 постов
            posts_text = combined[:MAX_POSTS_CHARS]
        else:
            posts_text = "(посты недоступны)"

        # Вызываем Qwen классификацию
        result = await qwen_ai_service.classify_channel(
            title=title or "—",
            username=username or "—",
            member_count=member_count or 0,
            description=description_trimmed or "(описание отсутствует)",
            posts=posts if posts else [],
            use_paid=False,  # Используем бесплатную модель
        )

        return ClassificationResult(
            topic=result.topic,
            subcategory=result.subcategory or "",
            confidence=result.confidence,
            rating=result.rating,
            reasoning=f"Qwen: {result.topic}",
            used_fallback=result.used_fallback,
        )

    except Exception as e:
        logger.warning(
            f"Qwen LLM classification failed for @{username}: {e}. Using fallback."
        )
        return ClassificationResult(
            topic="Другое",
            subcategory="",
            confidence=0.0,
            rating=5.0,
            reasoning="LLM недоступен",
            used_fallback=True,
        )


def _extract_json(text: str) -> dict:
    """
    Извлечь JSON из ответа LLM.
    LLM иногда оборачивает JSON в ```json ... ``` — обрабатываем это.
    """
    text = text.strip()

    # Убираем markdown-блоки если есть
    if "```" in text:
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Ищем JSON-объект
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"JSON не найден в ответе: {text[:100]}")

    return json.loads(text[start:end])
