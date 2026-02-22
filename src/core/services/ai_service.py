"""
AI Service для генерации рекламных текстов через Claude API.
Поддерживает кэширование в Redis, A/B тестирование и fallback на OpenAI.
"""

import asyncio
import hashlib
import json
import logging
from decimal import Decimal

import redis.asyncio as redis
from anthropic import AsyncAnthropic, RateLimitError
from openai import AsyncOpenAI

from src.config.settings import settings
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

# Константы
DEFAULT_CACHE_TTL = 3600  # 1 час
DEFAULT_TIMEOUT = 30  # секунд
MAX_RETRIES = 3


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
        self._anthropic_client: AsyncAnthropic | None = None
        self._openai_client: AsyncOpenAI | None = None
        self._redis: redis.Redis | None = None

    @property
    def anthropic_client(self) -> AsyncAnthropic:
        """Ленивая инициализация Anthropic клиента."""
        if self._anthropic_client is None:
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self._anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._anthropic_client

    @property
    def openai_client(self) -> AsyncOpenAI:
        """Ленивая инициализация OpenAI клиента."""
        if self._openai_client is None:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai_client

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
        """
        Получить ключ кэша для промпта.

        Args:
            prompt: Текст промпта.

        Returns:
            MD5 хэш промпта.
        """
        return f"ai_cache:{hashlib.md5(prompt.encode()).hexdigest()}"

    async def _check_cache(self, key: str) -> str | None:
        """
        Проверить кэш.

        Args:
            key: Ключ кэша.

        Returns:
            Значение из кэша или None.
        """
        try:
            redis_client = await self.redis_client
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def _set_cache(self, key: str, value: str, ttl: int = DEFAULT_CACHE_TTL) -> None:
        """
        Сохранить в кэш.

        Args:
            key: Ключ кэша.
            value: Значение.
            ttl: Время жизни в секундах.
        """
        try:
            redis_client = await self.redis_client
            await redis_client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
    ) -> str:
        """
        Вызвать Claude API.

        Args:
            system_prompt: Системный промпт.
            user_prompt: Пользовательский промпт.
            max_tokens: Максимальное количество токенов.

        Returns:
            Ответ от Claude.
        """
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    timeout=DEFAULT_TIMEOUT,
                )
                return response.content[0].text

            except RateLimitError:
                logger.warning(f"Claude rate limit exceeded, attempt {attempt + 1}")
                if attempt == MAX_RETRIES - 1:
                    # Fallback на OpenAI
                    return await self._call_openai(system_prompt, user_prompt, max_tokens)
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Claude API error (attempt {attempt + 1}): {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        # Должны вернуться из цикла раньше
        raise RuntimeError("Unexpected error in Claude API call")

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
    ) -> str:
        """
        Вызвать OpenAI GPT-4o API (fallback).

        Args:
            system_prompt: Системный промпт.
            user_prompt: Пользовательский промпт.
            max_tokens: Максимальное количество токенов.

        Returns:
            Ответ от GPT-4o.
        """
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            timeout=DEFAULT_TIMEOUT,
        )
        return response.choices[0].message.content or ""

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
            tone: Тон текста (нейтральный, дружеский, официальный).
            length: Длина текста (короткий, средний, длинный).
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

        # Проверяем и списываем баланс
        cost = settings.ai_cost_per_generation
        if not await self._deduct_balance(user_id, Decimal(str(cost))):
            raise ValueError(f"Insufficient balance. Required: {cost} RUB")

        # Системный промпт
        system_prompt = (
            "Ты профессиональный копирайтер рекламных текстов для Telegram. "
            "Создавай цепляющие, лаконичные тексты с эмодзи. "
            "Избегай запрещённых тем (лекарства, политика, 18+)."
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
        result = await self._call_claude(system_prompt, user_prompt, max_tokens=500)

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

        system_prompt = (
            "Ты профессиональный копирайтер. Создавай разные варианты текстов "
            "для A/B тестирования. Каждый вариант должен быть уникальным по стилю."
        )

        user_prompt = (
            f"Создай {count} различных варианта рекламного текста для A/B теста.\n\n"
            f"Описание: {description}\n\n"
            f"Раздели варианты разделителем '---' на отдельной строке."
        )

        result = await self._call_claude(system_prompt, user_prompt, max_tokens=1500)

        # Парсим варианты по разделителю
        variants = [v.strip() for v in result.split("\n---\n") if v.strip()]

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
            improvement_type: Тип улучшения (shorter, more_engaging, formal, casual).

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

        result = await self._call_claude(system_prompt, user_prompt, max_tokens=1000)

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

        # Списываем баланс (50% от стоимости генерации)
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

        result = await self._call_claude(system_prompt, user_prompt, max_tokens=200)

        # Парсим хэштеги
        hashtags = [h.strip() for h in result.replace("#", "").split(",") if h.strip()]
        hashtags = [f"#{h}" for h in hashtags[:count]]

        # Кэширование
        await self._set_cache(cache_key, json.dumps(hashtags))

        logger.info(f"Generated {len(hashtags)} hashtags for user {user_id}")
        return hashtags


# Глобальный экземпляр
ai_service = AIService()
