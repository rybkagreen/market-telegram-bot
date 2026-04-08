---
name: pytest-async
description: "MUST BE USED for async testing: pytest-asyncio auto mode, testcontainers with real PostgreSQL, mocking external APIs (YooKassa, Mistral, Telegram), FastAPI TestClient. Use when writing tests/, configuring coverage gates ≥80%, or adding fixtures in conftest.py. Enforces: testcontainers for integration tests, mock for external services only, .env.test for test config."
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# Pytest Async Conventions

Создаёт тесты на pytest-asyncio с реальным PostgreSQL через testcontainers.
Все внешние сервисы (Telegram API, Claude, YooKassa) — через `unittest.mock`.

## When to Use
- Написание unit-тестов для сервисов в `tests/unit/`
- Написание интеграционных тестов для репозиториев в `tests/integration/`
- Тестирование API-эндпоинтов FastAPI в `tests/api/`
- Написание тестов для content filter
- Настройка pytest fixtures (conftest.py)
- Настройка coverage-отчётов

## Rules
- Все async-тесты: `@pytest.mark.asyncio`
- Unit-тесты: мокать ВСЕ внешние вызовы (DB, Redis, API)
- Integration-тесты: использовать `testcontainers` (реальный PostgreSQL + Redis в Docker)
- Никогда не использовать production `.env` в тестах — использовать `.env.test`
- Цели покрытия: >80% для сервисов, 100% для критических путей (billing, filter)

## Instructions

1. Unit-тест: мокай зависимости через `unittest.mock.AsyncMock`
2. Integration-тест: используй `PostgresContainer` из testcontainers
3. API-тест: используй `AsyncClient` из httpx с `ASGITransport`
4. Фикстуры с базой данных — `scope="session"` для контейнера, `scope="function"` для сессии
5. Запускай: `pytest tests/ --cov=src --cov-report=term-missing`

## Examples

### Integration Test Fixtures (conftest.py)
```python
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.db.base import Base

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7") as r:
        yield r

@pytest.fixture(scope="session")
async def engine(postgres_container):
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def async_session(engine) -> AsyncSession:
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session_factory() as session:
        yield session
        await session.rollback()
```

### Integration Test — Repository
```python
import pytest
from decimal import Decimal
from src.db.repositories.user import UserRepository
from src.exceptions import InsufficientBalanceError

@pytest.mark.asyncio
async def test_create_user(async_session):
    repo = UserRepository(async_session)
    user = await repo.create_or_update(telegram_id=123456, username="testuser")
    assert user.telegram_id == 123456
    assert user.balance == Decimal("0.00")

@pytest.mark.asyncio
async def test_update_balance_insufficient(async_session):
    repo = UserRepository(async_session)
    user = await repo.create_or_update(telegram_id=999, username="poor")
    with pytest.raises(InsufficientBalanceError):
        await repo.update_balance(user.id, delta=Decimal("-100.00"))
```

### Unit Test — Service with Mocks
```python
import pytest
from unittest.mock import AsyncMock, patch
from src.services.campaign import CampaignService

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_by_user.return_value = []
    return repo

@pytest.mark.asyncio
async def test_list_campaigns_empty(mock_repo):
    with patch("src.services.campaign.CampaignRepository", return_value=mock_repo):
        service = CampaignService(session=AsyncMock())
        campaigns = await service.list_for_user(user_id=1)
    assert campaigns == []
    mock_repo.get_by_user.assert_awaited_once_with(1, page=1)
```

### API Test — FastAPI Endpoint
```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app

@pytest.mark.asyncio
async def test_list_campaigns_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/campaigns")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_campaigns_ok(async_session, test_user_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/campaigns",
            headers={"x-telegram-init-data": test_user_token}
        )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### pytest.ini / pyproject.toml
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
env_files = [".env.test"]
addopts = "--tb=short -v"
```
