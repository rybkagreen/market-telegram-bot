"""
Логирование использования токенов Qwen/OpenRouter API.

Сохраняет статистику в Redis для мониторинга расходов.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class TokenUsageLogger:
    """Логгер использования токенов."""

    def __init__(self, redis: Redis | None = None) -> None:
        """
        Инициализация логгера.

        Args:
            redis: Redis клиент для хранения статистики.
        """
        self._redis = redis

    async def log_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        task_type: str = "unknown",  # moderation, classification, generation
        user_id: int | None = None,
        cost_usd: float = 0.0,
    ) -> None:
        """
        Записать использование токенов.

        Args:
            model: Использованная модель.
            prompt_tokens: Токены промпта.
            completion_tokens: Токены ответа.
            total_tokens: Всего токенов.
            task_type: Тип задачи (moderation, classification, generation).
            user_id: ID пользователя (опционально).
            cost_usd: Стоимость в USD (если известна).
        """
        if not self._redis:
            logger.debug("Redis not configured, skipping token logging")
            return

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "task_type": task_type,
            "user_id": user_id,
            "cost_usd": cost_usd,
        }

        # Сохраняем в Redis list для истории
        await self._redis.lpush("qwen:token_usage", json.dumps(log_entry))

        # Храним последние 1000 записей
        await self._redis.ltrim("qwen:token_usage", 0, 999)

        # Агрегируем статистику по моделям
        model_key = f"qwen:stats:{model}"
        await self._redis.hincrby(model_key, "total_requests", 1)
        await self._redis.hincrby(model_key, "total_tokens", total_tokens)
        await self._redis.hincrby(model_key, "prompt_tokens", prompt_tokens)
        await self._redis.hincrby(model_key, "completion_tokens", completion_tokens)
        if cost_usd > 0:
            await self._redis.hincrbyfloat(model_key, "total_cost_usd", cost_usd)

        # TTL для статистики — 30 дней
        await self._redis.expire(model_key, 86400 * 30)

        logger.debug(f"Token usage: {model} | {total_tokens} tokens | {task_type}")

    async def get_stats(self, model: str | None = None) -> dict[str, Any]:
        """
        Получить статистику использования.

        Args:
            model: Конкретная модель или None для всех.

        Returns:
            Статистика использования токенов.
        """
        if not self._redis:
            return {}

        if model:
            stats = await self._redis.hgetall(f"qwen:stats:{model}")
            return {k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in stats.items()}

        # Статистика по всем моделям
        all_stats = {}
        async for key in self._redis.scan_iter("qwen:stats:*"):
            model_name = key.decode().replace("qwen:stats:", "")
            stats = await self._redis.hgetall(key)
            all_stats[model_name] = {
                k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in stats.items()
            }

        return all_stats

    async def get_recent_usage(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Получить последние записи использования.

        Args:
            limit: Количество записей.

        Returns:
            Список последних записей.
        """
        if not self._redis:
            return []

        entries = await self._redis.lrange("qwen:token_usage", 0, limit - 1)
        return [json.loads(e) for e in entries]


# Глобальный экземпляр
token_logger = TokenUsageLogger()
