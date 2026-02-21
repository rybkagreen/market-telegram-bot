---
name: sqlalchemy-repository
description: >
  Creates SQLAlchemy 2.0 async repositories, models, and queries following
  the project's Repository pattern. Use when writing new DB models in
  src/db/models/, new repository methods in src/db/repositories/, or
  composing complex async queries. Enforces: Generic BaseRepository[T],
  asyncpg driver, no ORM lazy-loading, atomic balance updates with RETURNING.
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# SQLAlchemy 2.0 Async Conventions

Создаёт модели и репозитории для PostgreSQL через SQLAlchemy 2.0 async + asyncpg.
Паттерн Repository изолирует логику работы с БД от бизнес-логики.

## When to Use
- Создание новых ORM-моделей в `src/db/models/`
- Написание методов репозитория в `src/db/repositories/`
- Составление сложных async-запросов с join, subquery, aggregate
- Атомарное обновление баланса пользователя
- Bulk upsert при импорте чатов
- Alembic-миграции

## Rules
- Все запросы через `await session.execute(select(...))`
- Никогда не использовать lazy relationships — всегда `selectinload` или `joinedload`
- Атомарные обновления: `UPDATE ... RETURNING` для изменений баланса
- Upsert: `insert().on_conflict_do_update()` для bulk-импорта
- Сессия всегда инжектируется — репозитории никогда не создают свои сессии

## Instructions

1. Модель наследует `Base` из `src/db/base.py`
2. Репозиторий наследует `BaseRepository[ModelClass]`
3. Для связей — явно указывай `lazy="raise"` чтобы поймать N+1 на этапе разработки
4. Для изменения баланса — только атомарный UPDATE с RETURNING
5. Покрой новый репозиторий интеграционными тестами через testcontainers

## Examples

### BaseRepository
```python
from typing import Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: int) -> T | None:
        return await self.session.get(self.model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, **data: object) -> T:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, id: int) -> bool:
        obj = await self.get(id)
        if not obj:
            return False
        await self.session.delete(obj)
        return True
```

### Atomic Balance Update
```python
from sqlalchemy import update
from decimal import Decimal
from src.db.models.user import User
from src.exceptions import InsufficientBalanceError

class UserRepository(BaseRepository[User]):
    model = User

    async def update_balance(self, user_id: int, delta: Decimal) -> Decimal:
        stmt = (
            update(User)
            .where(User.id == user_id, User.balance + delta >= 0)
            .values(balance=User.balance + delta)
            .returning(User.balance)
        )
        result = await self.session.execute(stmt)
        new_balance = result.scalar_one_or_none()
        if new_balance is None:
            raise InsufficientBalanceError(user_id=user_id)
        return new_balance
```

### Bulk Upsert
```python
from sqlalchemy.dialects.postgresql import insert

async def bulk_upsert_chats(self, chats: list[dict]) -> int:
    stmt = insert(Chat).values(chats)
    stmt = stmt.on_conflict_do_update(
        index_elements=["telegram_id"],
        set_={"title": stmt.excluded.title, "members_count": stmt.excluded.members_count}
    )
    result = await self.session.execute(stmt)
    return result.rowcount
```

### Query with eager loading
```python
from sqlalchemy.orm import selectinload

async def get_with_campaigns(self, user_id: int) -> User | None:
    result = await self.session.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.campaigns))
    )
    return result.scalar_one_or_none()
```
