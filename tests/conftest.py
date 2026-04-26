"""
Конфигурация и фикстуры для тестов.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable
from datetime import date
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.services.placement_request_service import PlacementRequestService
from src.core.services.reputation_service import ReputationService
from src.db.base import Base
from src.db.models.telegram_chat import TelegramChat

# from src.db.models.campaign import Campaign  # REMOVED in v4.2 — using PlacementRequest instead
from src.db.models.user import User
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepo

# ────────────────────────────────────────────
# Event loop fixtures
# ────────────────────────────────────────────


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    """Function-scoped event loop — matches asyncio_default_fixture_loop_scope=function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)


# ────────────────────────────────────────────
# Database fixtures
# ────────────────────────────────────────────


@pytest.fixture(scope="session")
def postgres_container() -> Any:
    """
    Создать PostgreSQL контейнер для тестов.

    Yields:
        PostgresContainer: Контейнер PostgreSQL.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres


def _dedupe_metadata_indexes() -> None:
    """Drop duplicate-named indexes from Base.metadata in-place.

    Some models (e.g. Act) declare the same index both via
    ``Column(..., index=True)`` and an explicit ``Index(...)`` in
    ``__table_args__``, so ``MetaData.create_all`` would raise
    ``DuplicateTable`` on the second index. Mirror of the same helper in
    ``tests/integration/conftest.py`` so root-suite tests can call
    ``create_all`` cleanly.
    """
    seen: set[str] = set()
    for table in Base.metadata.tables.values():
        for ix in list(table.indexes):
            if ix.name is not None and ix.name in seen:
                table.indexes.discard(ix)
            elif ix.name is not None:
                seen.add(ix.name)


@pytest_asyncio.fixture(scope="function")
async def test_engine(postgres_container: Any) -> AsyncGenerator[Any]:
    """Function-scoped async engine bound to the session-wide postgres_container.

    Each test starts with a freshly recreated ``public`` schema (DROP SCHEMA
    CASCADE + CREATE SCHEMA + create_all). DROP-then-CREATE is used instead
    of ``Base.metadata.drop_all`` because the model graph contains
    unresolvable foreign-key cycles between ``acts``, ``contracts``,
    ``invoices``, ``placement_requests`` and ``transactions`` — the same
    reason ``tests/integration/conftest.py`` uses ``DROP SCHEMA CASCADE``.
    """
    from sqlalchemy import text

    _dedupe_metadata_indexes()
    db_url = postgres_container.get_connection_url()
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: Any) -> AsyncGenerator[AsyncSession]:
    """Сессия БД с автоматическим rollback после каждого теста."""
    async_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


# ────────────────────────────────────────────
# In-memory SQLite fixtures for unit tests
# ────────────────────────────────────────────


@pytest_asyncio.fixture
async def sqlite_engine() -> Any:
    """In-memory SQLite движок для unit-тестов."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def sqlite_session(sqlite_engine: Any) -> AsyncGenerator[AsyncSession]:
    """Сессия SQLite с автоматическим rollback."""
    async_session = async_sessionmaker(
        sqlite_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


# ────────────────────────────────────────────
# Redis fixture
# ────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis_client() -> Redis:
    """Redis клиент на тестовой БД (индекс 2)."""
    client = Redis.from_url("redis://localhost:6379/2", decode_responses=True)
    yield client
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def mock_redis() -> Any:
    """
    Мок Redis клиента для unit-тестов.

    Returns:
        MagicMock: Мок клиента.
    """
    from unittest.mock import AsyncMock, MagicMock

    redis_client = MagicMock()
    redis_client.get = AsyncMock(return_value=None)
    redis_client.setex = AsyncMock()
    return redis_client


# ────────────────────────────────────────────
# API client fixture
# ────────────────────────────────────────────


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient]:
    """HTTP клиент для тестирования FastAPI."""
    from src.api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def api_client_no_auth() -> AsyncGenerator[AsyncClient]:
    """HTTP клиент для тестирования FastAPI без авторизации (public endpoints)."""
    from src.api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ────────────────────────────────────────────
# Bot mocks
# ────────────────────────────────────────────


@pytest.fixture
def mock_bot() -> Any:
    """
    Мок aiogram Bot.

    Returns:
        MagicMock: Мок бота.
    """
    from unittest.mock import AsyncMock, MagicMock

    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.session = AsyncMock()
    bot.session.close = AsyncMock()
    return bot


@pytest.fixture
def mock_anthropic_client() -> Any:
    """
    Мок Anthropic клиента.

    Returns:
        MagicMock: Мок клиента.
    """
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock()
    return client


@pytest.fixture
def mock_openai_client() -> Any:
    """
    Мок OpenAI клиента.

    Returns:
        MagicMock: Мок клиента.
    """
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    return client


# ────────────────────────────────────────────
# AI Service fixtures
# ────────────────────────────────────────────


@pytest.fixture
def mock_ai_service() -> Any:
    """
    Мок AI Service для тестов.

    Returns:
        MagicMock: Мок сервиса.
    """
    from unittest.mock import AsyncMock, MagicMock

    service = MagicMock()
    service.generate_ad_text = AsyncMock(return_value="Generated ad text")
    service.generate_ab_variants = AsyncMock(return_value=["Variant 1", "Variant 2"])
    service.improve_text = AsyncMock(return_value="Improved text")
    service.generate_hashtags = AsyncMock(return_value=["#tag1", "#tag2"])
    return service


# ────────────────────────────────────────────
# Test data helpers
# ────────────────────────────────────────────


@pytest.fixture
def user_test_data() -> dict[str, Any]:
    """Тестовые данные для пользователя."""
    return {
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "ru",
    }


@pytest.fixture
def campaign_test_data() -> dict[str, Any]:
    """Тестовые данные для кампании."""
    return {
        "title": "Test Campaign",
        "text": "Test ad text for campaign",
        "ai_description": "AI generated description",
        "filters_json": {"topics": ["business"], "min_members": 1000},
    }


@pytest.fixture
def chat_test_data() -> dict[str, Any]:
    """Тестовые данные для чата."""
    return {
        "telegram_id": -1001234567890,
        "title": "Test Channel",
        "username": "test_channel",
        "member_count": 5000,
        "topic": "business",
    }


# =============================================================================
# FIXTURES ДЛЯ PLACEMENT/ARBITRATION/REPUTATION ТЕСТОВ
# =============================================================================


@pytest.fixture
def advertiser_test_data() -> dict[str, Any]:
    """Тестовые данные для рекламодателя."""
    return {
        "telegram_id": 111111111,
        "username": "advertiser",
        "first_name": "Advertiser",
        "balance_rub": 5000,
        "referral_code": "adv_ref_001",
    }


@pytest.fixture
def owner_test_data() -> dict[str, Any]:
    """Тестовые данные для владельца канала."""
    return {
        "telegram_id": 222222222,
        "username": "owner",
        "first_name": "Owner",
        "balance_rub": 1000,
        "referral_code": "own_ref_001",
    }


@pytest.fixture
def channel_test_data() -> dict[str, Any]:
    """Тестовые данные для канала."""
    return {
        "telegram_id": -1009876543210,
        "title": "Test Channel",
        "username": "test_channel",
        "member_count": 5000,
        "is_active": True,
    }


@pytest_asyncio.fixture
async def advertiser_user(db_session: AsyncSession, advertiser_test_data: dict) -> User:
    """Создать тестового рекламодателя."""
    from src.db.models.user import User

    user = User(**advertiser_test_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession, owner_test_data: dict) -> User:
    """Создать тестового владельца."""
    from src.db.models.user import User

    user = User(**owner_test_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_channel(
    db_session: AsyncSession,
    channel_test_data: dict,
    owner_user: User,
) -> TelegramChat:
    """Создать тестовый канал."""
    from src.db.models.telegram_chat import TelegramChat

    channel = TelegramChat(**channel_test_data, owner_user_id=owner_user.id)
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def test_campaign(db_session: AsyncSession, advertiser_user: User):
    """Создать тестовую кампанию — REMOVED in v4.2."""
    # from src.db.models.campaign import Campaign, CampaignStatus
    # campaign = Campaign(...)
    # This fixture is deprecated — use placement_request fixture instead
    pytest.skip("Campaign model removed in v4.2 — use PlacementRequest")
    return None


@pytest_asyncio.fixture
async def placement_request_service(db_session: AsyncSession) -> PlacementRequestService:
    """Создать PlacementRequestService для тестов."""

    return PlacementRequestService(
        session=db_session,
        placement_repo=PlacementRequestRepository(db_session),
        channel_settings_repo=ChannelSettingsRepo(db_session),
        reputation_repo=ReputationRepo(db_session),
        billing_service=None,
    )


@pytest_asyncio.fixture
async def reputation_service(db_session: AsyncSession) -> ReputationService:
    """Создать ReputationService для тестов."""

    return ReputationService(
        session=db_session,
        reputation_repo=ReputationRepo(db_session),
    )


@pytest_asyncio.fixture
async def channel_settings_repo(db_session: AsyncSession) -> ChannelSettingsRepo:
    """Создать ChannelSettingsRepo для тестов."""

    return ChannelSettingsRepo(db_session)


@pytest_asyncio.fixture
async def placement_request_repo(db_session: AsyncSession) -> PlacementRequestRepository:
    """Создать PlacementRequestRepository для тестов."""

    return PlacementRequestRepository(db_session)


@pytest_asyncio.fixture
async def reputation_repo(db_session: AsyncSession) -> ReputationRepo:
    """Создать ReputationRepo для тестов."""

    return ReputationRepo(db_session)


@pytest_asyncio.fixture
async def api_client_with_auth(advertiser_user: User) -> AsyncGenerator[AsyncClient]:
    """HTTP клиент с авторизацией через JWT."""
    from src.api.auth_utils import create_access_token
    from src.api.main import app

    token = create_access_token(advertiser_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        yield client


# =============================================================================
# LEGAL PROFILE / CONTRACT / ORD fixtures (testing-suite 2026-04-21)
# =============================================================================


def _compute_inn10_checksum(first_9: str) -> str:
    """Compute the 10th digit of a 10-digit INN."""
    weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    total = sum(w * int(d) for w, d in zip(weights, first_9, strict=True))
    return str((total % 11) % 10)


def _compute_inn12_checksum(first_10: str) -> str:
    """Compute the 2 check digits for a 12-digit INN."""
    w1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    w2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    c1 = (sum(w * int(d) for w, d in zip(w1, first_10, strict=True)) % 11) % 10
    first_11 = first_10 + str(c1)
    c2 = (sum(w * int(d) for w, d in zip(w2, first_11, strict=True)) % 11) % 10
    return f"{c1}{c2}"


def make_valid_inn10(first_9: str = "770708389") -> str:
    """Build a 10-digit INN with a valid checksum (default: Yandex LLC)."""
    return first_9 + _compute_inn10_checksum(first_9)


def make_valid_inn12(first_10: str = "1234567890") -> str:
    """Build a 12-digit INN with valid checksums."""
    return first_10 + _compute_inn12_checksum(first_10)


def make_valid_ogrn(first_12: str = "102770013219") -> str:
    """Build a 13-digit OGRN with a valid checksum (default: Yandex LLC)."""
    check = (int(first_12) % 11) % 10
    return first_12 + str(check)


def make_valid_ogrnip(first_14: str = "30450011600001") -> str:
    """Build a 15-digit OGRNIP with a valid checksum."""
    check = (int(first_14) % 13) % 10
    return first_14 + str(check)


# Pre-computed valid test values (shared across tests)
VALID_INN10 = make_valid_inn10()  # 10 digits — legal_entity
VALID_INN12 = make_valid_inn12()  # 12 digits — individual / ip / self_employed
VALID_OGRN = make_valid_ogrn()
VALID_OGRNIP = make_valid_ogrnip()
VALID_KPP = "770701001"
VALID_BIK = "044525225"


@pytest.fixture
def legal_profile_data() -> Callable[[str], dict[str, Any]]:
    """Factory that returns valid `create_profile` payloads for each legal_status.

    Keys match columns on LegalProfile; checksums are pre-computed and valid.
    """

    def _build(status: str) -> dict[str, Any]:
        if status == "legal_entity":
            return {
                "legal_status": "legal_entity",
                "legal_name": "ООО «Тест»",
                "inn": VALID_INN10,
                "kpp": VALID_KPP,
                "ogrn": VALID_OGRN,
                "address": "г. Москва, ул. Льва Толстого, 16",
                "bank_name": "Сбербанк",
                "bank_account": "40702810123456789012",
                "bank_bik": VALID_BIK,
                "bank_corr_account": "30101810400000000225",
            }
        if status == "individual_entrepreneur":
            return {
                "legal_status": "individual_entrepreneur",
                "legal_name": "ИП Иванов И. И.",
                "inn": VALID_INN12,
                "ogrnip": VALID_OGRNIP,
                "address": "г. Москва, ул. Арбат, 1",
                "tax_regime": "usn_d",
                "bank_name": "Сбербанк",
                "bank_account": "40802810123456789012",
                "bank_bik": VALID_BIK,
                "bank_corr_account": "30101810400000000225",
            }
        if status == "self_employed":
            return {
                "legal_status": "self_employed",
                "legal_name": "Сидоров Сидор Сидорович",
                "inn": VALID_INN12,
                "yoomoney_wallet": "41001234567890",
            }
        if status == "individual":
            return {
                "legal_status": "individual",
                "legal_name": "Петров Петр Петрович",
                "passport_series": "4500",
                "passport_number": "123456",
                "passport_issued_by": "ОУФМС России по гор. Москве",
                "passport_issue_date": date(2020, 5, 15),
            }
        raise ValueError(f"Unknown legal_status: {status!r}")

    return _build


@pytest_asyncio.fixture
async def user_with_legal_profile(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> Callable[[str, int], Any]:
    """Factory: создать User + LegalProfile с валидными данными для нужного статуса."""
    from src.core.services.legal_profile_service import LegalProfileService
    from src.db.models.user import User

    counter = {"n": 0}

    async def _build(status: str, telegram_id: int | None = None) -> tuple[User, Any]:
        counter["n"] += 1
        tg_id = telegram_id if telegram_id is not None else 900_000_000 + counter["n"]
        user = User(
            telegram_id=tg_id,
            username=f"user_{tg_id}",
            first_name=f"Test {status}",
            balance_rub=0,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        svc = LegalProfileService(db_session)
        profile = await svc.create_profile(user.id, legal_profile_data(status))
        await db_session.flush()
        return user, profile

    return _build
