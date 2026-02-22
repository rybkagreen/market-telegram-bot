---
name: python-async
description: >
  Generates correct async Python 3.13 code for this project.
  Use when writing or editing any async function, coroutine, context manager,
  or asyncio pattern. Enforces project conventions: no blocking calls in
  async context, proper exception handling, type hints on all signatures.
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# Python Async Conventions

Обеспечивает правильное написание асинхронного кода на Python 3.13 в рамках проекта.
Все операции I/O должны быть неблокирующими, все подписи функций — типизированы.

## When to Use
- Написание любой `async def` функции
- Использование `asyncio`, `await`, `async with`, `async for`
- Работа с HTTP-клиентами, сессиями БД, файлами
- Конкурентное выполнение задач через `asyncio.gather()`
- Написание async-генераторов и async context managers

## Rules
- Все I/O должны быть `await`-ед — никогда не вызывать blocking-функции внутри `async def`
- Использовать `asyncio.gather()` для конкурентных задач, `asyncio.sleep()` для задержек
- Всегда добавлять возвращаемый тип: `async def foo() -> ReturnType:`
- Использовать `async with` для context managers (сессии, локи, HTTP-клиенты)
- Ловить конкретные исключения, никогда `except:` без типа

## Instructions

1. Убедись, что функция помечена `async def`
2. Все вызовы I/O операций — через `await`
3. Добавь аннотации типов на параметры и возвращаемое значение
4. Оберни работу с ресурсами в `async with`
5. Используй `try/except` с конкретными типами исключений

## Examples

### Async generator для потоковой обработки
```python
from typing import AsyncIterator
from sqlalchemy import select
from src.db.models import Result
from src.utils.helpers import chunks

async def stream_results(ids: list[int]) -> AsyncIterator[Result]:
    async with get_session() as session:
        for chunk in chunks(ids, size=100):
            results = await session.execute(
                select(Result).where(Result.id.in_(chunk))
            )
            for row in results.scalars():
                yield row
```

### Конкурентные задачи
```python
import asyncio

async def fetch_all(user_ids: list[int]) -> list[dict]:
    tasks = [fetch_user(uid) for uid in user_ids]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Async context manager
```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def managed_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```
