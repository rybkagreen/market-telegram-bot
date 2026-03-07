"""
AI сервис на базе OpenRouter.

Единственный провайдер для всего бота.
Использует бесплатную Qwen модель для всех тарифов (режим отладки).

Документация OpenRouter: https://openrouter.ai/docs
"""

import hashlib
import logging
from typing import Any

from openai import AsyncOpenAI

from src.api.constants.ai import (
    AI_MAX_TOKENS,
    AI_TEMPERATURE,
    FALLBACK_MODEL,
    FREE_MODEL,
    TOPIC_PROMPTS,
)
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Системный промпт по умолчанию
AD_SYSTEM_PROMPT = TOPIC_PROMPTS["default"]


class AIService:
    """
    Сервис для AI-генерации текстов через OpenRouter.

    Автоматически выбирает модель по тарифу пользователя.
    Кэширует результаты в Redis (TTL 1 час) для экономии токенов.
    """

    def __init__(self, redis: Any | None = None) -> None:
        """
        Инициализация сервиса.

        Args:
            redis: Redis клиент для кэширования (опционально).
        """
        self._client: AsyncOpenAI | None = None
        self._redis = redis

    @property
    def client(self) -> AsyncOpenAI:
        """Ленивая инициализация OpenAI-compatible клиента для OpenRouter."""
        if self._client is None:
            if not settings.openrouter_api_key:
                raise RuntimeError(
                    "OPENROUTER_API_KEY не задан в .env. Получить ключ: https://openrouter.ai/keys"
                )
            self._client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                timeout=settings.ai_timeout,
                default_headers={
                    # Обязательные заголовки OpenRouter
                    "HTTP-Referer": "https://github.com/rybkagreen/market-telegram-bot",
                    "X-OpenRouter-Title": "Market Telegram Bot",
                },
            )
            logger.info("OpenRouter client initialized")
        return self._client

    # ──────────────────────────────────────────────────────────────
    # Публичные методы
    # ──────────────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system: str = AD_SYSTEM_PROMPT,
        user_plan: str = "free",
        use_cache: bool = True,
        topic: str | None = None,
    ) -> str:
        """
        Сгенерировать текст через OpenRouter.

        Использует бесплатную Qwen модель для всех тарифов (режим отладки).

        Args:
            prompt: Пользовательский промпт.
            system: Системный промпт (по умолчанию — копирайтер).
            user_plan: Тариф пользователя (не используется, все на бесплатной модели).
            use_cache: Использовать кэш Redis.
            topic: Тематика для выбора стиля (education, retail, finance, default).

        Returns:
            Сгенерированный текст.

        Raises:
            RuntimeError: при ошибке API или отсутствии ключа.
        """
        # Выбираем системный промпт по тематике
        if topic and topic in TOPIC_PROMPTS:
            system = TOPIC_PROMPTS[topic]
            logger.debug(f"Using topic prompt: {topic}")

        # Используем бесплатную Qwen модель для всех (режим отладки)
        model = FREE_MODEL
        logger.debug(f"Using free model: {model}")

        # Проверяем кэш
        if use_cache and self._redis:
            cache_key = self._make_cache_key(model, system, prompt)
            cached = await self._get_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for model={model}")
                return cached

        # Вызов API
        result = await self._call_api(model=model, system=system, prompt=prompt)

        # Сохраняем в кэш
        if use_cache and self._redis:
            await self._set_cache(cache_key, result, ttl=3600)

        return result

    async def generate_ad_text(
        self,
        description: str,
        user_plan: str = "free",
        topic: str | None = None,
    ) -> str:
        """
        Сгенерировать рекламный текст по описанию продукта.

        Args:
            description: Описание продукта/услуги от пользователя.
            user_plan: Тариф (не используется, все на бесплатной модели).
            topic: Тематика для выбора стиля (education, retail, finance, default).

        Returns:
            Готовый рекламный текст для Telegram (300-700 символов).
        """
        # Формируем краткий промпт
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
        return await self.generate(prompt=prompt, user_plan=user_plan, topic=topic, use_cache=False)

    async def generate_ab_variants(
        self,
        description: str,
        user_plan: str = "free",
        count: int = 3,
        topic: str | None = None,
    ) -> list[str]:
        """
        Сгенерировать несколько вариантов для A/B теста.

        Args:
            description: Описание продукта/услуги.
            user_plan: Тариф пользователя.
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
        raw = await self.generate(
            prompt=prompt,
            user_plan=user_plan,
            topic=topic,
            use_cache=False,
        )

        # Парсим варианты по разделителю
        variants = [v.strip() for v in raw.split("---") if v.strip()]
        return variants[:count] if len(variants) >= count else variants

    async def improve_text(
        self,
        original: str,
        mode: str = "engaging",
        user_plan: str = "free",
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
            user_plan: Тариф пользователя.

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
        return await self.generate(prompt=prompt, user_plan=user_plan)

    async def generate_hashtags(
        self,
        text: str,
        user_plan: str = "free",
    ) -> list[str]:
        """
        Сгенерировать хэштеги для рекламного текста.

        Args:
            text: Рекламный текст.
            user_plan: Тариф пользователя.

        Returns:
            Список хэштегов (5-10 штук).
        """
        prompt = (
            f"Придумай 7 релевантных хэштегов для этого рекламного поста.\n\n"
            f"Текст:\n{text}\n\n"
            f"Формат: каждый хэштег с # на отдельной строке. Только хэштеги, ничего лишнего."
        )
        raw = await self.generate(prompt=prompt, user_plan=user_plan)
        tags = [line.strip() for line in raw.splitlines() if line.strip().startswith("#")]
        return tags[:10]

    # ──────────────────────────────────────────────────────────────
    # Внутренние методы
    # ──────────────────────────────────────────────────────────────

    async def _call_api(self, model: str, system: str, prompt: str) -> str:
        """
        Выполнить запрос к OpenRouter API.

        Args:
            model: ID модели в формате OpenRouter.
            system: Системный промпт.
            prompt: Пользовательский промпт.

        Returns:
            Ответ модели.

        Raises:
            RuntimeError: при ошибке API.
        """
        # Пробуем основную модель
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=AI_MAX_TOKENS,
                temperature=AI_TEMPERATURE,
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("Пустой ответ от модели")
            logger.info(
                f"OpenRouter OK: model={model}, tokens={response.usage.total_tokens if response.usage else '?'}"
            )
            return content.strip()

        except Exception as e:
            # Проверяем rate limit
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                # Пробуем fallback модель
                logger.warning(
                    f"Rate limit on {model}, trying fallback: {FALLBACK_MODEL}"
                )
                try:
                    response = await self.client.chat.completions.create(
                        model=FALLBACK_MODEL,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=AI_MAX_TOKENS,
                        temperature=AI_TEMPERATURE,
                    )
                    content = response.choices[0].message.content
                    if not content:
                        raise RuntimeError("Пустой ответ от fallback модели")
                    logger.info(
                        f"OpenRouter OK (fallback): model={FALLBACK_MODEL}, tokens={response.usage.total_tokens if response.usage else '?'}"
                    )
                    return content.strip()
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed: {fallback_error}")
                    raise RuntimeError(
                        f"Ошибка AI генерации (fallback не удался): {fallback_error}"
                    ) from fallback_error

            # Другие ошибки
            logger.error(f"OpenRouter API error: model={model}, error={e}")
            raise RuntimeError(f"Ошибка AI генерации: {e}") from e

    def _make_cache_key(self, model: str, system: str, prompt: str) -> str:
        """Сформировать ключ кэша Redis."""
        raw = f"{model}:{system[:50]}:{prompt}"
        return f"ai_cache:{hashlib.md5(raw.encode()).hexdigest()}"

    async def _get_cache(self, key: str) -> str | None:
        """Получить значение из Redis кэша."""
        if not self._redis:
            return None
        try:
            value = await self._redis.get(key)
            return value.decode() if isinstance(value, bytes) else value
        except Exception:
            return None

    async def _set_cache(self, key: str, value: str, ttl: int = 3600) -> None:
        """Сохранить значение в Redis кэше."""
        if not self._redis:
            return
        try:
            await self._redis.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")


# ──────────────────────────────────────────────────────────────
# Синглтоны
# ──────────────────────────────────────────────────────────────

# Основной сервис (без кэша — Redis подключается в main.py)
ai_service = AIService()

# Алиас для совместимости с admin.py где используется admin_ai_service
admin_ai_service = ai_service
