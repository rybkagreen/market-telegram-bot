"""
AI сервис на базе OpenRouter.

Единственный провайдер для всего бота.
Модель зависит от тарифа пользователя:
  FREE/STARTER  → meta-llama/llama-4-scout:free  (бесплатно)
  PRO/BUSINESS  → anthropic/claude-sonnet-4.6    (платно)

Документация OpenRouter: https://openrouter.ai/docs
"""

import hashlib
import logging
from typing import Any

from openai import AsyncOpenAI

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Системный промпт для генерации рекламных текстов
AD_SYSTEM_PROMPT = """Ты — профессиональный копирайтер для Telegram.
Пишешь короткие, цепляющие рекламные тексты на русском языке.
Используй эмодзи уместно. Текст должен быть живым, не шаблонным.
Не используй маркеры списков — только сплошной текст или абзацы.
Максимальная длина ответа — 500 слов."""


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
    ) -> str:
        """
        Сгенерировать текст через OpenRouter.

        Автоматически выбирает модель по тарифу.
        Кэширует результат в Redis если доступен.

        Args:
            prompt: Пользовательский промпт.
            system: Системный промпт (по умолчанию — копирайтер).
            user_plan: Тариф пользователя ("free", "starter", "pro", "business").
            use_cache: Использовать кэш Redis.

        Returns:
            Сгенерированный текст.

        Raises:
            RuntimeError: при ошибке API или отсутствии ключа.
        """
        model = settings.get_model_for_plan(user_plan)

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
    ) -> str:
        """
        Сгенерировать рекламный текст по описанию продукта.

        Args:
            description: Описание продукта/услуги от пользователя.
            user_plan: Тариф (определяет модель).

        Returns:
            Готовый рекламный текст для Telegram.
        """
        prompt = (
            f"Напиши рекламный текст для Telegram-канала.\n\n"
            f"Описание продукта/услуги:\n{description}\n\n"
            f"Требования:\n"
            f"- Длина 150-300 слов\n"
            f"- Цепляющий заголовок первой строкой\n"
            f"- Призыв к действию в конце\n"
            f"- Уместные эмодзи\n"
            f"- Живой, не шаблонный язык"
        )
        return await self.generate(prompt=prompt, user_plan=user_plan)

    async def generate_ab_variants(
        self,
        description: str,
        user_plan: str = "free",
        count: int = 3,
    ) -> list[str]:
        """
        Сгенерировать несколько вариантов рекламного текста для A/B теста.

        Args:
            description: Описание продукта/услуги.
            user_plan: Тариф пользователя.
            count: Количество вариантов (по умолчанию 3).

        Returns:
            Список вариантов текста.
        """
        prompt = (
            f"Напиши {count} разных варианта рекламного текста для Telegram.\n\n"
            f"Описание:\n{description}\n\n"
            f"Требования к каждому варианту:\n"
            f"- 100-250 слов\n"
            f"- Разные стили (один — эмоциональный, один — информативный, один — с акцентом на выгоду)\n"
            f"- Разделяй варианты строкой: ---\n"
            f"- Нумерацию не добавляй — только тексты\n"
            f"- Уместные эмодзи"
        )
        raw = await self.generate(
            prompt=prompt,
            user_plan=user_plan,
            use_cache=False,  # A/B варианты не кэшируем — нужна уникальность
        )

        # Парсим варианты по разделителю ---
        variants = [v.strip() for v in raw.split("---") if v.strip()]
        # Берём ровно count вариантов
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
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.ai_max_tokens,
                temperature=settings.ai_temperature,
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("Пустой ответ от модели")
            logger.info(
                f"OpenRouter OK: model={model}, tokens={response.usage.total_tokens if response.usage else '?'}"
            )
            return content.strip()

        except Exception as e:
            logger.error(f"OpenRouter API error: model={model}, error={e}")
            raise RuntimeError(f"Ошибка AI генерации: {e}") from e

    def _make_cache_key(self, model: str, system: str, prompt: str) -> str:
        """Сформировать ключ кэша Redis."""
        raw = f"{model}:{system[:50]}:{prompt}"
        return f"ai_cache:{hashlib.md5(raw.encode()).hexdigest()}"

    async def _get_cache(self, key: str) -> str | None:
        """Получить значение из Redis кэша."""
        try:
            value = await self._redis.get(key)
            return value
        except Exception:
            return None

    async def _set_cache(self, key: str, value: str, ttl: int = 3600) -> None:
        """Сохранить значение в Redis кэше."""
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
