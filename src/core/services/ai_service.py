"""
AI Service — провайдер-агностичный сервис генерации текста.

Переключение между провайдерами через AI_PROVIDER в .env:
  groq      — бесплатный, рекомендован для разработки
  openai    — production
  anthropic — production
  mock      — заглушка для тестов без API
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from decimal import Decimal

import redis.asyncio as redis

from src.config.settings import settings
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Константы
DEFAULT_CACHE_TTL = 3600  # 1 час
DEFAULT_TIMEOUT = 30  # секунд
MAX_RETRIES = 3


# ─────────────────────────────────────────────
# Base Provider Interface
# ─────────────────────────────────────────────

class BaseLLMProvider(ABC):
    """Базовый интерфейс для всех LLM провайдеров."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        """Сгенерировать текст по промту."""

    @abstractmethod
    async def generate_variants(self, prompt: str, count: int = 3) -> list[str]:
        """Сгенерировать несколько вариантов текста."""


# ─────────────────────────────────────────────
# Groq Provider (бесплатный)
# ─────────────────────────────────────────────

class GroqProvider(BaseLLMProvider):
    """Groq API провайдер — бесплатный LLM API."""

    def __init__(self) -> None:
        from groq import AsyncGroq
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.ai_model

    async def generate(self, prompt: str, system: str = "") -> str:
        """
        Сгенерировать текст через Groq API.

        Args:
            prompt: Пользовательский промпт.
            system: Системный промпт (опционально).

        Returns:
            Сгенерированный текст.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
        )
        return response.choices[0].message.content.strip()

    async def generate_variants(self, prompt: str, count: int = 3) -> list[str]:
        """
        Сгенерировать A/B варианты текста.

        Args:
            prompt: Описание продукта/услуги.
            count: Количество вариантов.

        Returns:
            Список вариантов текстов.
        """
        system = (
            "Ты профессиональный копирайтер рекламных текстов для Telegram. "
            "Пиши короткие (2-4 предложения), цепляющие тексты на русском языке. "
            "Используй 2-3 эмодзи. Добавляй призыв к действию."
        )
        full_prompt = (
            f"Напиши {count} разных варианта рекламного текста для Telegram.\n"
            f"Тема: {prompt}\n\n"
            f"Формат ответа — каждый вариант с новой строки через разделитель '---'"
        )
        raw = await self.generate(full_prompt, system=system)
        return self._parse_variants(raw, count)

    @staticmethod
    def _parse_variants(raw: str, count: int) -> list[str]:
        """
        Разбить ответ LLM на отдельные варианты.

        Args:
            raw: Сырой ответ от LLM.
            count: Ожидаемое количество вариантов.

        Returns:
            Список вариантов.
        """
        # Сначала пробуем разделить по ---
        variants = [v.strip() for v in raw.split("---") if v.strip()]

        # Если не сработало — разбиваем по нумерации
        if len(variants) < count:
            lines = [line.strip() for line in raw.split("\n") if line.strip()]
            variants = []
            current = []
            for line in lines:
                if line[:2] in ("1.", "2.", "3.", "4.", "5."):
                    if current:
                        variants.append(" ".join(current))
                    current = [line[2:].strip()]
                else:
                    current.append(line)
            if current:
                variants.append(" ".join(current))

        # Если всё ещё мало — разбиваем по пустым строкам
        if len(variants) < count:
            variants = [v.strip() for v in raw.split("\n\n") if v.strip()]

        return variants[:count] if variants else [raw]


# ─────────────────────────────────────────────
# OpenAI Provider (для production)
# ─────────────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API провайдер для production."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.ai_model or "gpt-4o-mini"

    async def generate(self, prompt: str, system: str = "") -> str:
        """Сгенерировать текст через OpenAI API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=settings.ai_max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def generate_variants(self, prompt: str, count: int = 3) -> list[str]:
        """Сгенерировать A/B варианты через OpenAI."""
        result = await self.generate(
            f"Напиши {count} варианта рекламного текста для Telegram по теме: {prompt}"
        )
        return GroqProvider._parse_variants(result, count)


# ─────────────────────────────────────────────
# Anthropic Provider (для production)
# ─────────────────────────────────────────────

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API провайдер для production."""

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = "claude-3-sonnet-20240229"

    async def generate(self, prompt: str, system: str = "") -> str:
        """Сгенерировать текст через Anthropic API."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=settings.ai_max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    async def generate_variants(self, prompt: str, count: int = 3) -> list[str]:
        """Сгенерировать A/B варианты через Anthropic."""
        result = await self.generate(
            f"Напиши {count} варианта рекламного текста для Telegram по теме: {prompt}",
            system="Ты профессиональный копирайтер для Telegram.",
        )
        return GroqProvider._parse_variants(result, count)


# ─────────────────────────────────────────────
# Mock Provider (для тестов)
# ─────────────────────────────────────────────

class MockProvider(BaseLLMProvider):
    """Mock провайдер для тестов без API ключа."""

    async def generate(self, prompt: str, system: str = "") -> str:
        """Вернуть заглушку вместо реального ответа."""
        return f"[MOCK] Сгенерированный текст для: {prompt}"

    async def generate_variants(self, prompt: str, count: int = 3) -> list[str]:
        """Вернуть mock варианты."""
        return [
            f"🚀 {prompt} — лучшее предложение месяца! Нажмите здесь.",
            f"💡 Откройте для себя {prompt}. Только сейчас со скидкой!",
            f"⭐ {prompt} — выбор тысяч клиентов. Попробуйте бесплатно!",
        ][:count]


# ─────────────────────────────────────────────
# Factory — выбор провайдера из .env
# ─────────────────────────────────────────────

def get_ai_provider() -> BaseLLMProvider:
    """
    Создать провайдер на основе настроек.

    Returns:
        Экземпляр провайдера.
    """
    provider = settings.ai_provider.lower()

    if provider == "groq":
        if not settings.groq_api_key:
            logger.warning("GROQ_API_KEY не задан, используется Mock провайдер")
            return MockProvider()
        return GroqProvider()

    elif provider == "openai":
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY не задан, используется Mock провайдер")
            return MockProvider()
        return OpenAIProvider()

    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY не задан, используется Mock провайдер")
            return MockProvider()
        return AnthropicProvider()

    elif provider == "mock":
        return MockProvider()

    else:
        logger.warning(f"Неизвестный AI_PROVIDER: {provider}, используется Mock")
        return MockProvider()


# ─────────────────────────────────────────────
# Public API сервиса
# ─────────────────────────────────────────────

class AIService:
    """
    Сервис для генерации рекламных текстов с помощью ИИ.

    Методы:
        generate_ad_text: Генерация рекламного текста
        generate_ab_variants: Генерация A/B вариантов
        improve_text: Улучшение текста
        generate_hashtags: Генерация хэштегов
    """

    def __init__(self) -> None:
        """Инициализация AI сервиса."""
        self._provider = get_ai_provider()
        self._redis: redis.Redis | None = None
        logger.info(f"AI Service инициализирован: {type(self._provider).__name__}")

    @property
    async def redis_client(self) -> redis.Redis:
        """Ленивая инициализация Redis клиента."""
        if self._redis is None:
            self._redis = redis.from_url(
                str(settings.redis_url),
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _get_cache_key(self, prompt: str) -> str:
        """Получить ключ кэша для промпта."""
        return f"ai_cache:{hashlib.md5(prompt.encode()).hexdigest()}"

    async def _check_cache(self, key: str) -> str | None:
        """Проверить кэш."""
        try:
            redis_client = await self.redis_client
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def _set_cache(self, key: str, value: str, ttl: int = DEFAULT_CACHE_TTL) -> None:
        """Сохранить в кэш."""
        try:
            redis_client = await self.redis_client
            await redis_client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def _deduct_balance(self, user_id: int, amount: Decimal) -> bool:
        """
        Списать баланс за генерацию.

        Args:
            user_id: ID пользователя.
            amount: Сумма для списания.

        Returns:
            True если списание успешно.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if user is None:
                return False

            if user.balance < amount:
                logger.warning(f"User {user_id} has insufficient balance: {user.balance}")
                return False

            await user_repo.update_balance(user_id, Decimal(-amount))
            return True

    async def generate_ad_text(
        self,
        user_id: int,
        description: str,
        tone: str = "нейтральный",
        length: str = "средний",
        audience: str = "широкая аудитория",
    ) -> str:
        """
        Генерировать рекламный текст.

        Args:
            user_id: ID пользователя.
            description: Описание продукта/услуги.
            tone: Тон текста.
            length: Длина текста.
            audience: Целевая аудитория.

        Returns:
            Сгенерированный текст.
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(f"{description}{tone}{length}{audience}")
        cached = await self._check_cache(cache_key)
        if cached:
            logger.info(f"AI cache hit for user {user_id}")
            return cached

        # Списываем баланс
        cost = settings.ai_cost_per_generation
        if not await self._deduct_balance(user_id, Decimal(str(cost))):
            raise ValueError(f"Insufficient balance. Required: {cost} RUB")

        # Системный промпт
        system_prompt = (
            "Ты профессиональный копирайтер рекламных текстов для Telegram. "
            "Создавай цепляющие, лаконичные тексты с эмодзи. "
            "Избегай запрещённых тем."
        )

        # Пользовательский промпт
        length_map = {
            "короткий": "50-100 символов",
            "средний": "150-300 символов",
            "длинный": "400-600 символов",
        }

        user_prompt = (
            f"Создай рекламный текст для Telegram.\n\n"
            f"Описание: {description}\n"
            f"Тон: {tone}\n"
            f"Длина: {length_map.get(length, 'средний')}\n"
            f"Аудитория: {audience}\n\n"
            f"Используй 2-3 эмодзи, добавь призыв к действию."
        )

        # Генерация
        result = await self._provider.generate(user_prompt, system_prompt)

        # Кэширование
        await self._set_cache(cache_key, result)

        logger.info(f"Generated ad text for user {user_id}, cost: {cost} RUB")
        return result

    async def generate_ab_variants(
        self,
        user_id: int,
        description: str,
        count: int = 3,
    ) -> list[str]:
        """
        Генерировать A/B варианты текста.

        Args:
            user_id: ID пользователя.
            description: Описание продукта/услуги.
            count: Количество вариантов.

        Returns:
            Список вариантов текстов.
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(f"ab_{description}_{count}")
        cached = await self._check_cache(cache_key)
        if cached:
            logger.info(f"AI A/B cache hit for user {user_id}")
            return cached.split("\n---\n")

        # Списываем баланс (умножаем на количество вариантов)
        cost = settings.ai_cost_per_generation * count
        if not await self._deduct_balance(user_id, Decimal(str(cost))):
            raise ValueError(f"Insufficient balance. Required: {cost} RUB")

        # Генерация
        variants = await self._provider.generate_variants(description, count)

        # Кэширование
        await self._set_cache(cache_key, "\n---\n".join(variants))

        logger.info(f"Generated {len(variants)} A/B variants for user {user_id}")
        return variants

    async def improve_text(
        self,
        user_id: int,
        original: str,
        improvement_type: str = "more_engaging",
    ) -> str:
        """
        Улучшить существующий текст.

        Args:
            user_id: ID пользователя.
            original: Исходный текст.
            improvement_type: Тип улучшения.

        Returns:
            Улучшенный текст.
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(f"improve_{original}_{improvement_type}")
        cached = await self._check_cache(cache_key)
        if cached:
            logger.info(f"AI improve cache hit for user {user_id}")
            return cached

        # Списываем баланс
        cost = settings.ai_cost_per_generation
        if not await self._deduct_balance(user_id, Decimal(str(cost))):
            raise ValueError(f"Insufficient balance. Required: {cost} RUB")

        improvement_prompts = {
            "shorter": "Сделай текст короче, сохранив основной смысл.",
            "more_engaging": "Сделай текст более цепляющим и эмоциональным.",
            "formal": "Сделай текст более официальным и профессиональным.",
            "casual": "Сделай текст более дружеским и неформальным.",
        }

        system_prompt = "Ты профессиональный редактор. Улучшай тексты, сохраняя смысл."

        user_prompt = (
            f"Улучши этот текст: {improvement_prompts.get(improvement_type, '')}\n\n"
            f"Исходный текст:\n{original}"
        )

        result = await self._provider.generate(user_prompt, system_prompt)

        # Кэширование
        await self._set_cache(cache_key, result)

        logger.info(f"Improved text for user {user_id}, type: {improvement_type}")
        return result

    async def generate_hashtags(
        self,
        user_id: int,
        text: str,
        count: int = 10,
    ) -> list[str]:
        """
        Генерировать хэштеги для текста.

        Args:
            user_id: ID пользователя.
            text: Текст для анализа.
            count: Количество хэштегов.

        Returns:
            Список хэштегов.
        """
        # Проверяем кэш
        cache_key = self._get_cache_key(f"hashtags_{text}_{count}")
        cached = await self._check_cache(cache_key)
        if cached:
            logger.info(f"AI hashtags cache hit for user {user_id}")
            return json.loads(cached)

        # Списываем баланс (50% от стоимости)
        cost = settings.ai_cost_per_generation * 0.5
        if not await self._deduct_balance(user_id, Decimal(str(cost))):
            raise ValueError(f"Insufficient balance. Required: {cost} RUB")

        system_prompt = (
            "Ты эксперт по хэштегам для Telegram. Подбирай релевантные, "
            "популярные хэштеги без пробелов."
        )

        user_prompt = (
            f"Сгенерируй {count} хэштегов для этого текста:\n\n{text}\n\n"
            f"Верни только список хэштегов через запятую, без пояснений."
        )

        result = await self._provider.generate(user_prompt, system_prompt)

        # Парсим хэштеги
        hashtags = [h.strip() for h in result.replace("#", "").split(",") if h.strip()]
        hashtags = [f"#{h}" for h in hashtags[:count]]

        # Кэширование
        await self._set_cache(cache_key, json.dumps(hashtags))

        logger.info(f"Generated {len(hashtags)} hashtags for user {user_id}")
        return hashtags

    async def check_text_quality(self, text: str) -> dict:
        """
        Оценить качество рекламного текста (0-100).

        Args:
            text: Текст для оценки.

        Returns:
            Словарь с оценкой и текстом.
        """
        prompt = (
            f"Оцени качество рекламного текста для Telegram по шкале 0-100.\n"
            f"Критерии: цепляемость, призыв к действию, эмодзи, длина.\n"
            f"Текст: {text}\n\n"
            f"Ответь только числом от 0 до 100."
        )
        try:
            result = await self._provider.generate(prompt)
            score = int("".join(filter(str.isdigit, result))[:3])
            return {"score": min(100, max(0, score)), "text": text}
        except Exception:
            return {"score": 50, "text": text}


# Глобальный экземпляр
ai_service = AIService()
