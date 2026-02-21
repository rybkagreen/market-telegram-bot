import asyncio
from time import time
from aiogram import BaseMiddleware
from aiogram.types import Message
from redis.asyncio import Redis


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов (0.5 сек)."""
    
    def __init__(self, redis: Redis, rate: float = 0.5):
        self.redis = redis
        self.rate = rate

    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        key = f"throttle:{user_id}"
        
        # Получаем время последнего запроса
        last_request = await self.redis.get(key)
        
        if last_request:
            elapsed = time() - float(last_request)
            if elapsed < self.rate:
                await event.answer("⏳ Подождите немного...")
                return
        
        # Обновляем время запроса
        await self.redis.set(key, time(), ex=60)
        
        return await handler(event, data)
