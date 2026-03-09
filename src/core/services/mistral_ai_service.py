"""
Mistral AI сервис для классификации, модерации и генерации контента.

Использует Mistral AI API через официальную библиотеку mistralai.
https://docs.mistral.ai/

Все методы асинхронные (используют asyncio.to_thread для неблокирующих вызовов).

Модели:
- mistral-medium-latest: для всех задач (классификация, модерация, генерация)
- mistral-agent: через beta.conversations.start
"""

import asyncio
import json
import logging
from dataclasses import dataclass

from mistralai import Mistral

from src.config.settings import settings
from src.constants.ai import (
    AI_MAX_TOKENS,
    AI_TEMPERATURE,
    DEFAULT_SYSTEM_PROMPT,
    MISTRAL_AGENT_ID,
    MISTRAL_AGENT_VERSION,
    MISTRAL_MODEL,
    TOPIC_PROMPTS,
)

logger = logging.getLogger(__name__)


@dataclass
class MistralClassificationResult:
    """Результат классификации канала."""

    topic: str  # Тематика канала
    subcategory: str | None  # Подкатегория
    rating: float  # Рейтинг (1-10)
    confidence: float  # Уверенность (0.0 - 1.0)


@dataclass
class MistralModerationResult:
    """Результат модерации контента."""

    passed: bool  # Прошел ли проверку
    score: float  # Оценка нарушений (0.0 - 1.0)
    categories: list[str]  # Категории нарушений
    analysis: str  # Краткий анализ


class MistralAIService:
    """
    Сервис для работы с Mistral AI.

    Специализирован для:
    - Классификации Telegram каналов
    - Модерации контента
    """

    # Системный промпт для классификации
    CLASSIFICATION_SYSTEM_PROMPT = """Ты — эксперт по классификации Telegram каналов.
Твоя задача — определить тематику канала по названию, описанию и постам.

Доступные тематики:
- бизнес: бизнес, финансы, инвестиции, стартапы
- маркетинг: маркетинг, реклама, SMM, продажи
- ит: IT, программирование, технологии, AI
- здоровье: здоровье, спорт, фитнес, медицина
- образование: образование, курсы, обучение
- новости: новости, СМИ, политика
- крипто: криптовалюта, блокчейн, Web3
- lifestyle: путешествия, еда, мода, развлечения
- другое: другое

Верни ответ ТОЛЬКО в формате JSON:
{
    "topic": "название тематики",
    "subcategory": "подкатегория или null",
    "rating": 1-10,
    "confidence": 0.0-1.0
}"""

    # Системный промпт для модерации
    MODERATION_SYSTEM_PROMPT = """Ты — модератор контента для Telegram бота.
Твоя задача — определить, содержит ли текст запрещенный контент по законодательству РФ.

Категории для проверки:
- drugs: наркотики, продажа, употребление
- terrorism: терроризм, призывы к насилию
- weapons: оружие, продажа оружия
- adult: порнография, эротика 18+
- fraud: мошенничество, обман, пирамиды
- suicide: суицид, призывы к самоубийству
- extremism: экстремизм, нацизм, разжигание розни
- gambling: азартные игры, казино, ставки

Верни ответ ТОЛЬКО в формате JSON:
{
    "passed": true/false,
    "score": 0.0-1.0,
    "categories": ["category1", "category2"],
    "analysis": "краткий анализ текста"
}"""

    def __init__(self) -> None:
        """Инициализация сервиса."""
        if not settings.mistral_api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY не задан в .env. "
                "Получить ключ: https://console.mistral.ai/api-keys"
            )
        self.client = Mistral(api_key=settings.mistral_api_key)

    async def classify_channel(
        self,
        title: str,
        description: str = "",
        username: str = "",
        member_count: int = 0,
        posts: list[str] | None = None,
    ) -> MistralClassificationResult:
        """
        Классифицировать Telegram канал.

        Args:
            title: Название канала.
            description: Описание канала.
            username: Username канала.
            member_count: Количество подписчиков.
            posts: Список последних постов.

        Returns:
            Результат классификации.
        """
        # Формируем входные данные
        input_data = f"""
Название: {title}
Username: @{username or "нет"}
Подписчиков: {member_count or "нет данных"}
Описание: {description or "нет описания"}
Последние посты: {posts[:3] if posts else "нет постов"}
""".strip()

        user_prompt = f"Классифицируй этот Telegram канал:\n\n{input_data}"

        try:
            # Выполняем синхронный вызов в отдельном потоке
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=MISTRAL_MODEL,
                messages=[
                    {"role": "system", "content": self.CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],  # type: ignore[arg-type]
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Пустой ответ от Mistral API")

            # Очищаем ответ от markdown кода если есть
            content = content.strip()  # type: ignore[union-attr]
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)

            return MistralClassificationResult(
                topic=result.get("topic", "другое"),
                subcategory=result.get("subcategory"),
                rating=float(result.get("rating", 5.0)),
                confidence=float(result.get("confidence", 0.5)),
            )

        except Exception as e:
            logger.error(f"Mistral classification error: {e}")
            # Fallback результат
            return MistralClassificationResult(
                topic="другое",
                subcategory=None,
                rating=5.0,
                confidence=0.0,
            )

    async def moderate_content(
        self,
        text: str,
    ) -> MistralModerationResult:
        """
        Проверить контент на запрещённые темы.

        Args:
            text: Текст для проверки.

        Returns:
            Результат модерации.
        """
        user_prompt = f"Проверь этот текст на запрещенный контент:\n\n{text[:3000]}"

        try:
            # Выполняем синхронный вызов в отдельном потоке
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=MISTRAL_MODEL,
                messages=[
                    {"role": "system", "content": self.MODERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],  # type: ignore[arg-type]
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Пустой ответ от Mistral API")

            # Очищаем ответ от markdown кода если есть
            content = content.strip()  # type: ignore[union-attr]
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)

            return MistralModerationResult(
                passed=result.get("passed", True),
                score=float(result.get("score", 0.0)),
                categories=result.get("categories", []),
                analysis=result.get("analysis", ""),
            )

        except Exception as e:
            logger.error(f"Mistral moderation error: {e}")
            # Fallback на безопасный режим
            return MistralModerationResult(
                passed=True,
                score=0.0,
                categories=[],
                analysis="",
            )

    async def classify_with_agent(
        self,
        title: str,
        description: str = "",
        username: str = "",
        member_count: int = 0,
    ) -> MistralClassificationResult:
        """
        Классифицировать канал через Mistral Agent (beta).

        Args:
            title: Название канала.
            description: Описание канала.
            username: Username канала.
            member_count: Количество подписчиков.

        Returns:
            Результат классификации.
        """
        inputs = [
            {
                "role": "user",
                "content": f"""Классифицируй Telegram канал:
Название: {title}
Username: @{username or "нет"}
Подписчиков: {member_count or "нет данных"}
Описание: {description or "нет описания"}

Верни JSON: {{"topic": "тематика", "subcategory": "подкатегория", "rating": 1-10, "confidence": 0.0-1.0}}""",
            }
        ]

        try:
            # Выполняем синхронный вызов в отдельном потоке
            response = await asyncio.to_thread(
                self.client.beta.conversations.start,
                agent_id=MISTRAL_AGENT_ID,
                agent_version=MISTRAL_AGENT_VERSION,
                inputs=inputs,  # type: ignore[arg-type]
            )

            # Получаем контент из ответа (outputs — список MessageOutputEntry)
            if not response.outputs or len(response.outputs) == 0:
                raise ValueError("Пустой ответ от Mistral Agent")

            # Type narrowing: проверяем тип первого элемента
            first_output = response.outputs[0]
            # Проверяем что это MessageOutputEntry с атрибутом content
            if not hasattr(first_output, 'content'):
                raise ValueError(f"Unexpected output type: {type(first_output)}")
            content = first_output.content
            if not content:
                raise ValueError("Пустой контент от Mistral Agent")

            # Очищаем ответ от markdown кода если есть
            content = content.strip()  # type: ignore[union-attr]
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)

            return MistralClassificationResult(
                topic=result.get("topic", "другое"),
                subcategory=result.get("subcategory"),
                rating=float(result.get("rating", 5.0)),
                confidence=float(result.get("confidence", 0.5)),
            )

        except Exception as e:
            logger.error(f"Mistral Agent classification error: {e}")
            return MistralClassificationResult(
                topic="другое",
                subcategory=None,
                rating=5.0,
                confidence=0.0,
            )

    # ──────────────────────────────────────────────────────────────
    # Методы генерации текста (для замены ai_service.py)
    # ──────────────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system: str = DEFAULT_SYSTEM_PROMPT,
        topic: str | None = None,
        use_cache: bool = False,
    ) -> str:
        """
        Сгенерировать текст через Mistral AI.

        Args:
            prompt: Пользовательский промпт.
            system: Системный промпт (по умолчанию — копирайтер).
            topic: Тематика для выбора стиля (education, retail, finance, default).
            use_cache: Не используется (оставлен для совместимости).

        Returns:
            Сгенерированный текст.
        """
        # Выбираем системный промпт по тематике
        if topic and topic in TOPIC_PROMPTS:
            system = TOPIC_PROMPTS[topic]
            logger.debug(f"Using topic prompt: {topic}")

        user_prompt = prompt

        try:
            # Выполняем синхронный вызов в отдельном потоке
            response = await asyncio.to_thread(
                self.client.chat.complete,
                model=MISTRAL_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],  # type: ignore[arg-type]
                max_tokens=AI_MAX_TOKENS,
                temperature=AI_TEMPERATURE,
            )

            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("Пустой ответ от модели")

            logger.info(
                f"Mistral OK: model={MISTRAL_MODEL}, tokens={response.usage.total_tokens if response.usage else '?'}"
            )
            return content.strip()  # type: ignore[union-attr]

        except Exception as e:
            logger.error(f"Mistral generation error: {e}")
            raise RuntimeError(f"Ошибка генерации текста: {e}") from e

    async def generate_ad_text(
        self,
        description: str,
        topic: str | None = None,
    ) -> str:
        """
        Сгенерировать рекламный текст по описанию продукта.

        Args:
            description: Описание продукта/услуги от пользователя.
            topic: Тематика для выбора стиля.

        Returns:
            Готовый рекламный текст для Telegram (300-700 символов).
        """
        prompt = (
            f"Напиши рекламный текст для Telegram-канала.\n\n"
            f"Описание:\n{description}\n\n"
            f"Требования:\n"
            f"- Длина 300-600 символов (кратко!)\n"
            f"- Цепляющий заголовок в первой строке\n"
            f"- Призыв к действию в конце\n"
            f"- Живой язык, без шаблонов\n"
            f"- Эмодзи только по делу"
        )
        return await self.generate(prompt=prompt, topic=topic, use_cache=False)

    async def generate_ab_variants(
        self,
        description: str,
        count: int = 3,
        topic: str | None = None,
    ) -> list[str]:
        """
        Сгенерировать несколько вариантов для A/B теста.

        Args:
            description: Описание продукта/услуги.
            count: Количество вариантов.
            topic: Тематика для выбора стиля.

        Returns:
            Список вариантов текста (каждый 300-600 символов).
        """
        prompt = (
            f"Напиши {count} РАЗНЫХ варианта рекламного текста для Telegram.\n\n"
            f"Описание:\n{description}\n\n"
            f"Требования к каждому:\n"
            f"- 300-600 символов (кратко!)\n"
            f"- Разные стили (эмоциональный / информативный / с выгодой)\n"
            f"- Разделяй варианты строкой: ---\n"
            f"- Без нумерации — только тексты"
        )
        raw = await self.generate(prompt=prompt, topic=topic, use_cache=False)

        # Парсим варианты по разделителю
        variants = [v.strip() for v in raw.split("---") if v.strip()]
        return variants[:count] if len(variants) >= count else variants

    async def improve_text(
        self,
        original: str,
        mode: str = "engaging",
    ) -> str:
        """
        Улучшить существующий текст.

        Args:
            original: Исходный текст.
            mode: Тип улучшения.
                  "engaging" — сделать живее
                  "shorter"  — сократить
                  "formal"   — формальный тон
                  "casual"   — разговорный тон

        Returns:
            Улучшенный текст.
        """
        mode_prompts = {
            "engaging": "Сделай текст более цепляющим и живым. Добавь эмоции.",
            "shorter": "Сократи текст в 2 раза, сохранив главное. Без потери смысла.",
            "formal": "Переведи в официально-деловой стиль. Без эмодзи.",
            "casual": "Переведи в разговорный дружеский стиль. Добавь эмодзи.",
        }
        instruction = mode_prompts.get(mode, mode_prompts["engaging"])

        prompt = f"{instruction}\n\nИсходный текст:\n{original}"
        return await self.generate(prompt=prompt)

    async def generate_hashtags(
        self,
        text: str,
    ) -> list[str]:
        """
        Сгенерировать хэштеги для рекламного текста.

        Args:
            text: Рекламный текст.

        Returns:
            Список хэштегов (5-10 штук).
        """
        prompt = (
            f"Придумай 7 релевантных хэштегов для этого рекламного поста.\n\n"
            f"Текст:\n{text}\n\n"
            f"Формат: каждый хэштег с # на отдельной строке. Только хэштеги, ничего лишнего."
        )
        raw = await self.generate(prompt=prompt)
        tags = [line.strip() for line in raw.splitlines() if line.strip().startswith("#")]
        return tags[:10]


# Глобальный экземпляр
mistral_ai_service = MistralAIService()

# Алиас для совместимости с кодом где используется ai_service
ai_service = mistral_ai_service
admin_ai_service = mistral_ai_service
