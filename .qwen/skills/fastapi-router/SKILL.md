---
name: fastapi-router
description: "MUST BE USED for FastAPI routers, JWT auth via Telegram initData HMAC-SHA256, Pydantic v2 schemas, dependency injection, OpenAPI specs, Mini App endpoints. Use when working with src/api/routers/, auth middleware, webhook handlers, or adding new API endpoints. Enforces: async route handlers, no business logic in routers, proper HTTP status codes."
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# FastAPI Router Conventions

Создаёт API-эндпоинты для Telegram Mini App на FastAPI 0.115+.
Аутентификация — через Telegram `initData` HMAC-SHA256. Все схемы — Pydantic v2.

## When to Use
- Добавление новых эндпоинтов в `src/api/routers/`
- Написание Pydantic v2 схем запроса/ответа
- Реализация зависимостей (auth, db, pagination)
- Подключение нового роутера к `src/api/main.py`
- Написание интеграционных тестов для API

## Rules
- Все route handlers — `async def`
- Всегда использовать Pydantic v2 (`model_config = ConfigDict(from_attributes=True)`)
- Инжектировать `current_user: User = Depends(get_current_user)` для защищённых роутов
- Возвращать осмысленные HTTP-статусы: 200, 201, 400, 401, 403, 404, 422
- Никакой бизнес-логики в роутерах — делегировать в сервисы

## Instructions

1. Создай файл в `src/api/routers/<feature>.py`
2. Определи `router = APIRouter(prefix="/<feature>", tags=["<feature>"])`
3. Напиши Pydantic схемы в `src/api/schemas/<feature>.py`
4. Используй `Depends()` для инжекции сессии БД и текущего пользователя
5. Подключи роутер в `src/api/main.py`: `app.include_router(feature_router)`

## Examples

### Router Pattern
```python
from fastapi import APIRouter, Depends, HTTPException, status
from src.api.dependencies import get_current_user, get_db
from src.api.schemas.campaign import CampaignCreate, CampaignResponse
from src.db.models.user import User
from src.db.repositories.campaign import CampaignRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    page: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CampaignResponse]:
    repo = CampaignRepository(db)
    campaigns = await repo.get_by_user(current_user.id, page=page)
    return [CampaignResponse.model_validate(c) for c in campaigns]

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    repo = CampaignRepository(db)
    campaign = await repo.create(user_id=current_user.id, **data.model_dump())
    return CampaignResponse.model_validate(campaign)
```

### Pydantic v2 Schemas
```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from decimal import Decimal
from enum import Enum

class CampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"

class CampaignCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    text: str = Field(min_length=10, max_length=4096)
    budget: Decimal = Field(gt=0, decimal_places=2)

class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: CampaignStatus
    budget: Decimal
    created_at: datetime
```

### Telegram initData Auth Dependency
```python
import hashlib
import hmac
from fastapi import Header, HTTPException, status
from urllib.parse import unquote, parse_qsl

async def get_current_user(
    x_telegram_init_data: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        data = dict(parse_qsl(unquote(x_telegram_init_data), strict_parsing=True))
        received_hash = data.pop("hash")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise ValueError("Invalid hash")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    telegram_id = int(json.loads(data["user"])["id"])
    user = await UserRepository(db).get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user
```
