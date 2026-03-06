"""
Qwen AI сервис для задач модерации и классификации.

Использует модели Qwen через OpenRouter API.
Оптимизирован для работы с русским языком.

Модели:
- qwen-2.5-coder-32b-instruct:free — бесплатная, для классификации
- qwen-turbo — дешёвая и быстрая ($0.002/1K tokens)
- qwen-plus — качественная ($0.04/1K tokens)
"""

import asyncio
import concurrent.futures
import json
import logging
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class QwenModerationResult:
    """Результат модерации контента."""

    passed: bool  # Прошел ли проверку
    score: float  # Оценка нарушений (0.0 - 1.0)
    categories: list[str]  # Категории нарушений
    analysis: str  # Краткий анализ


@dataclass
class QwenClassificationResult:
    """Результат классификации канала."""

    topic: str  # Тематика канала
    subcategory: str | None  # Подкатегория
    rating: float  # Рейтинг (1-10)
    confidence: float  # Уверенность (0.0 - 1.0)
    used_fallback: bool  # Использовался ли fallback


class QwenAIService:
    """
    Сервис для работы с Qwen моделями через OpenRouter.

    Специализирован для:
    - Модерации контента (проверка на запрещённые темы)
    - Классификации Telegram каналов
    """

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
}

Правила оценки:
- Если текст чистый → passed: true, score: 0.0
- Если текст содержит нарушения → passed: false, score: 0.5-1.0
- Если текст сомнительный → passed: false, score: 0.3-0.5"""

    # Системный промпт для классификации
    CLASSIFICATION_SYSTEM_PROMPT = """Ты — эксперт по классификации Telegram каналов.
Твоя задача — определить тематику канала по названию, описанию и постам.

Доступные тематики:
- business: бизнес, финансы, инвестиции, стартапы
- marketing: маркетинг, реклама, SMM, продажи
- it: IT, программирование, технологии, AI
- health: здоровье, спорт, фитнес, медицина
- education: образование, курсы, обучение
- news: новости, СМИ, политика
- crypto: криптовалюта, блокчейн, Web3
- lifestyle: путешествия, еда, мода, развлечения
- other: другое

Верни ответ ТОЛЬКО в формате JSON:
{
    "topic": "название тематики",
    "subcategory": "подкатегория или null",
    "rating": 1-10,
    "confidence": 0.0-1.0,
    "reasoning": "краткое обоснование"
}

Правила оценки рейтинга:
- 8-10: качественный канал с уникальным контентом
- 6-7: хороший канал со стандартным контентом
- 4-5: средний канал, есть проблемы
- 1-3: низкое качество, спам или неактивен"""

    def __init__(self, redis: Any | None = None) -> None:
        """
        Инициализация сервиса.

        Args:
            redis: Redis клиент для логирования токенов (опционально).
        """
        self._client: AsyncOpenAI | None = None
        self._redis = redis
        self._token_logger = None

        if redis:
            from src.core.services.token_logger import TokenUsageLogger

            self._token_logger = TokenUsageLogger(redis)

    @property
    def client(self) -> AsyncOpenAI:
        """Ленивая инициализация клиента."""
        if self._client is None:
            if not settings.openrouter_api_key:
                raise RuntimeError(
                    "OPENROUTER_API_KEY не задан. Получить: https://openrouter.ai/keys"
                )
            self._client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/rybkagreen/market-telegram-bot",
                    "X-OpenRouter-Title": "Market Telegram Bot - Qwen",
                },
            )
        return self._client

    def _get_model(self, use_paid: bool = False, for_moderation: bool = True) -> str:
        """
        Получить модель для запроса.

        Args:
            use_paid: Использовать платную модель или нет.
            for_moderation: Если True, используем Step (без rate limit),
                           если False — Qwen (для классификации).

        Returns:
            ID модели в формате OpenRouter.
        """
        if use_paid:
            return settings.model_qwen_plus

        # Для модерации используем Step (без rate limit)
        # Для классификации используем Qwen (лучше качество)
        if for_moderation:
            return settings.model_free  # stepfun/step-3.5-flash:free
        return settings.model_qwen_coder_free  # qwen/qwen3-coder:free

    async def _call_qwen_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> str:
        """
        Вызвать Qwen API асинхронно.

        Args:
            system_prompt: Системный промпт.
            user_prompt: Пользовательский промпт.
            model: Модель для использования.
            temperature: Температура генерации.
            max_tokens: Максимальное количество токенов.

        Returns:
            Ответ от модели.
        """
        model = model or self._get_model()

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        # Логирование использования токенов
        if self._token_logger and hasattr(response, "usage") and response.usage:
            await self._token_logger.log_usage(
                model=model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                task_type="moderation"
                if "модератор" in system_prompt.lower()
                else "classification",
            )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Пустой ответ от Qwen API")

        return content

    def _call_qwen_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
        timeout: int = 30,
    ) -> str:
        """
        Вызвать Qwen API синхронно (для Celery workers).

        Args:
            system_prompt: Системный промпт.
            user_prompt: Пользовательский промпт.
            model: Модель для использования.
            temperature: Температура генерации.
            max_tokens: Максимальное количество токенов.
            timeout: Таймаут в секундах.

        Returns:
            Ответ от модели.
        """

        async def _call() -> str:
            return await self._call_qwen_async(
                system_prompt, user_prompt, model, temperature, max_tokens
            )

        # Выполняем в отдельном потоке для совместимости с Celery
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, _call())
            return future.result(timeout=timeout)

    async def moderate_content(
        self,
        text: str,
        use_paid: bool = False,
    ) -> QwenModerationResult:
        """
        Проверить контент на запрещённые темы.
        Использует Step model (без rate limit).

        Args:
            text: Текст для проверки.
            use_paid: Использовать платную модель.

        Returns:
            Результат модерации.
        """
        model = self._get_model(use_paid, for_moderation=True)
        user_prompt = f"Проверь этот текст на запрещенный контент:\n\n{text[:3000]}"

        try:
            content = await self._call_qwen_async(
                self.MODERATION_SYSTEM_PROMPT,
                user_prompt,
                model,
            )

            result = json.loads(content)

            return QwenModerationResult(
                passed=result.get("passed", True),
                score=float(result.get("score", 0.0)),
                categories=result.get("categories", []),
                analysis=result.get("analysis", ""),
            )

        except Exception as e:
            logger.error(f"Qwen moderation error: {e}")
            # Fallback на безопасный режим
            return QwenModerationResult(passed=True, score=0.0, categories=[], analysis="")

    def moderate_content_sync(
        self,
        text: str,
        use_paid: bool = False,
        timeout: int = 30,
    ) -> QwenModerationResult:
        """
        Проверить контент синхронно (для Celery).

        Args:
            text: Текст для проверки.
            use_paid: Использовать платную модель.
            timeout: Таймаут в секундах.

        Returns:
            Результат модерации.
        """
        model = self._get_model(use_paid)
        user_prompt = f"Проверь этот текст на запрещенный контент:\n\n{text[:3000]}"

        try:
            content = self._call_qwen_sync(
                self.MODERATION_SYSTEM_PROMPT,
                user_prompt,
                model,
                timeout=timeout,
            )

            result = json.loads(content)

            return QwenModerationResult(
                passed=result.get("passed", True),
                score=float(result.get("score", 0.0)),
                categories=result.get("categories", []),
                analysis=result.get("analysis", ""),
            )

        except Exception as e:
            logger.error(f"Qwen moderation sync error: {e}")
            return QwenModerationResult(passed=True, score=0.0, categories=[], analysis="")

    async def classify_channel(
        self,
        title: str,
        description: str = "",
        username: str = "",
        member_count: int = 0,
        posts: list[str] | None = None,
        use_paid: bool = False,
    ) -> QwenClassificationResult:
        """
        Классифицировать Telegram канал.
        Использует Qwen model (лучшее качество для классификации).

        Args:
            title: Название канала.
            description: Описание канала.
            username: Username канала.
            member_count: Количество подписчиков.
            posts: Список последних постов.
            use_paid: Использовать платную модель.

        Returns:
            Результат классификации.
        """
        model = self._get_model(use_paid, for_moderation=False)

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
            content = await self._call_qwen_async(
                self.CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt,
                model,
                temperature=0.2,  # Более детерминированный ответ
            )

            result = json.loads(content)

            return QwenClassificationResult(
                topic=result.get("topic", "other"),
                subcategory=result.get("subcategory"),
                rating=float(result.get("rating", 5.0)),
                confidence=float(result.get("confidence", 0.5)),
                used_fallback=False,
            )

        except Exception as e:
            logger.error(f"Qwen classification error: {e}")
            # Fallback результат
            return QwenClassificationResult(
                topic="other",
                subcategory=None,
                rating=5.0,
                confidence=0.0,
                used_fallback=True,
            )

    def classify_channel_sync(
        self,
        title: str,
        description: str = "",
        username: str = "",
        member_count: int = 0,
        posts: list[str] | None = None,
        use_paid: bool = False,
        timeout: int = 30,
    ) -> QwenClassificationResult:
        """
        Классифицировать канал синхронно (для Celery).

        Args:
            title: Название канала.
            description: Описание канала.
            username: Username канала.
            member_count: Количество подписчиков.
            posts: Список последних постов.
            use_paid: Использовать платную модель.
            timeout: Таймаут в секундах.

        Returns:
            Результат классификации.
        """
        model = self._get_model(use_paid)

        input_data = f"""
Название: {title}
Username: @{username or "нет"}
Подписчиков: {member_count or "нет данных"}
Описание: {description or "нет описания"}
Последние посты: {posts[:3] if posts else "нет постов"}
""".strip()

        user_prompt = f"Классифицируй этот Telegram канал:\n\n{input_data}"

        try:
            content = self._call_qwen_sync(
                self.CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt,
                model,
                temperature=0.2,
                timeout=timeout,
            )

            result = json.loads(content)

            return QwenClassificationResult(
                topic=result.get("topic", "other"),
                subcategory=result.get("subcategory"),
                rating=float(result.get("rating", 5.0)),
                confidence=float(result.get("confidence", 0.5)),
                used_fallback=False,
            )

        except Exception as e:
            logger.error(f"Qwen classification sync error: {e}")
            return QwenClassificationResult(
                topic="other",
                subcategory=None,
                rating=5.0,
                confidence=0.0,
                used_fallback=True,
            )


# Глобальный экземпляр
qwen_ai_service = QwenAIService()
