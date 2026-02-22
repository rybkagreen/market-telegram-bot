"""
Интеграционные тесты для репозиториев с testcontainers.
"""

import pytest
from decimal import Decimal
from testcontainers.postgres import PostgresContainer

from src.db.models.user import User, UserPlan
from src.db.models.campaign import Campaign, CampaignStatus
from src.db.repositories.base import BaseRepository
from src.db.repositories.user_repo import UserRepository
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.session import get_async_engine, async_sessionmaker


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    """
    Создать PostgreSQL контейнер для тестов.

    Yields:
        PostgresContainer: Контейнер PostgreSQL.
    """
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture
async def db_session(postgres_container: PostgresContainer):
    """
    Создать сессию БД для теста.

    Yields:
        AsyncSession: Сессия БД.
    """
    from src.db.base import Base

    engine = get_async_engine(postgres_container.get_connection_url())
    async_session = async_sessionmaker(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


class TestUserRepository:
    """Тесты UserRepository."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session) -> None:
        """Проверка создания пользователя."""
        user_repo = UserRepository(db_session)

        user = await user_repo.create({
            "telegram_id": 123456789,
            "username": "testuser",
            "referral_code": "ABC123",
        })

        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.balance == Decimal("0.00")
        assert user.plan == UserPlan.FREE

    @pytest.mark.asyncio
    async def test_get_by_telegram_id(self, db_session) -> None:
        """Проверка поиска по Telegram ID."""
        user_repo = UserRepository(db_session)

        # Создаём пользователя
        await user_repo.create({
            "telegram_id": 987654321,
            "username": "findme",
            "referral_code": "XYZ789",
        })

        # Ищем
        user = await user_repo.get_by_telegram_id(987654321)

        assert user is not None
        assert user.username == "findme"

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found(self, db_session) -> None:
        """Проверка отсутствия пользователя."""
        user_repo = UserRepository(db_session)

        user = await user_repo.get_by_telegram_id(999999999)

        assert user is None

    @pytest.mark.asyncio
    async def test_update_balance(self, db_session) -> None:
        """Проверка обновления баланса."""
        user_repo = UserRepository(db_session)

        # Создаём пользователя с балансом 100
        user = await user_repo.create({
            "telegram_id": 111222333,
            "username": "balance_test",
            "referral_code": "BAL123",
            "balance": Decimal("100.00"),
        })

        # Списываем 30
        await user_repo.update_balance(user.id, Decimal("-30.00"))

        # Проверяем
        updated_user = await user_repo.get_by_id(user.id)
        assert updated_user.balance == Decimal("70.00")

    @pytest.mark.asyncio
    async def test_update_balance_negative(self, db_session) -> None:
        """Проверка обновления баланса (уход в минус)."""
        user_repo = UserRepository(db_session)

        user = await user_repo.create({
            "telegram_id": 444555666,
            "username": "negative_balance",
            "referral_code": "NEG123",
            "balance": Decimal("10.00"),
        })

        # Списываем больше чем есть
        await user_repo.update_balance(user.id, Decimal("-50.00"))

        updated_user = await user_repo.get_by_id(user.id)
        assert updated_user.balance == Decimal("-40.00")

    @pytest.mark.asyncio
    async def test_create_or_update_exists(self, db_session) -> None:
        """Проверка обновления существующего пользователя."""
        user_repo = UserRepository(db_session)

        # Создаём
        await user_repo.create({
            "telegram_id": 777888999,
            "username": "original",
            "referral_code": "ORI123",
        })

        # Обновляем
        user = await user_repo.create_or_update(
            telegram_id=777888999,
            username="updated",
        )

        assert user.username == "updated"

    @pytest.mark.asyncio
    async def test_create_or_update_new(self, db_session) -> None:
        """Проверка создания нового пользователя."""
        user_repo = UserRepository(db_session)

        user = await user_repo.create_or_update(
            telegram_id=123123123,
            username="newuser",
            referral_code="NEW123",
        )

        assert user.telegram_id == 123123123
        assert user.username == "newuser"


class TestCampaignRepository:
    """Тесты CampaignRepository."""

    @pytest.mark.asyncio
    async def test_create_campaign(self, db_session) -> None:
        """Проверка создания кампании."""
        # Сначала создаём пользователя
        user_repo = UserRepository(db_session)
        user = await user_repo.create({
            "telegram_id": 555666777,
            "username": "campaign_owner",
            "referral_code": "CAM123",
        })

        campaign_repo = CampaignRepository(db_session)

        campaign = await campaign_repo.create({
            "user_id": user.id,
            "title": "Test Campaign",
            "text": "Test ad text",
            "status": CampaignStatus.DRAFT,
        })

        assert campaign.title == "Test Campaign"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.user_id == user.id

    @pytest.mark.asyncio
    async def test_get_by_user(self, db_session) -> None:
        """Проверка получения кампаний пользователя."""
        user_repo = UserRepository(db_session)
        user = await user_repo.create({
            "telegram_id": 888999000,
            "username": "multi_campaign",
            "referral_code": "MUL123",
        })

        campaign_repo = CampaignRepository(db_session)

        # Создаём 3 кампании
        for i in range(3):
            await campaign_repo.create({
                "user_id": user.id,
                "title": f"Campaign {i}",
                "text": f"Text {i}",
                "status": CampaignStatus.DRAFT,
            })

        # Получаем
        campaigns, total = await campaign_repo.get_by_user(
            user_id=user.id,
            page=1,
            page_size=10,
        )

        assert total == 3
        assert len(campaigns) == 3

    @pytest.mark.asyncio
    async def test_update_status(self, db_session) -> None:
        """Проверка обновления статуса кампании."""
        user_repo = UserRepository(db_session)
        user = await user_repo.create({
            "telegram_id": 111000999,
            "username": "status_test",
            "referral_code": "STA123",
        })

        campaign_repo = CampaignRepository(db_session)

        campaign = await campaign_repo.create({
            "user_id": user.id,
            "title": "Status Test",
            "text": "Test",
            "status": CampaignStatus.DRAFT,
        })

        # Обновляем статус
        updated = await campaign_repo.update_status(
            campaign_id=campaign.id,
            status=CampaignStatus.QUEUED,
        )

        assert updated.status == CampaignStatus.QUEUED

    @pytest.mark.asyncio
    async def test_get_scheduled_due(self, db_session) -> None:
        """Проверка получения запланированных кампаний."""
        from datetime import datetime, UTC, timedelta

        user_repo = UserRepository(db_session)
        user = await user_repo.create({
            "telegram_id": 222333444,
            "username": "scheduled_test",
            "referral_code": "SCH123",
        })

        campaign_repo = CampaignRepository(db_session)

        # Создаём кампанию с прошедшим scheduled_at
        past_time = datetime.now(UTC) - timedelta(hours=1)
        await campaign_repo.create({
            "user_id": user.id,
            "title": "Scheduled Past",
            "text": "Test",
            "status": CampaignStatus.QUEUED,
            "scheduled_at": past_time,
        })

        # Создаём кампанию с будущим scheduled_at
        future_time = datetime.now(UTC) + timedelta(hours=1)
        await campaign_repo.create({
            "user_id": user.id,
            "title": "Scheduled Future",
            "text": "Test",
            "status": CampaignStatus.QUEUED,
            "scheduled_at": future_time,
        })

        # Получаем готовые к запуску
        scheduled = await campaign_repo.get_scheduled_due()

        assert len(scheduled) == 1
        assert scheduled[0].title == "Scheduled Past"


class TestBaseRepository:
    """Тесты BaseRepository."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session) -> None:
        """Проверка получения по ID."""
        user_repo = UserRepository(db_session)

        user = await user_repo.create({
            "telegram_id": 999888777,
            "username": "base_test",
            "referral_code": "BAS123",
        })

        found = await user_repo.get_by_id(user.id)

        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_delete(self, db_session) -> None:
        """Проверка удаления."""
        user_repo = UserRepository(db_session)

        user = await user_repo.create({
            "telegram_id": 666555444,
            "username": "delete_test",
            "referral_code": "DEL123",
        })

        # Удаляем
        deleted = await user_repo.delete(user.id)

        assert deleted is True

        # Проверяем что удалён
        found = await user_repo.get_by_id(user.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_paginate(self, db_session) -> None:
        """Проверка пагинации."""
        user_repo = UserRepository(db_session)

        # Создаём 25 пользователей
        for i in range(25):
            await user_repo.create({
                "telegram_id": 100000000 + i,
                "username": f"user{i}",
                "referral_code": f"PAG{i:03d}",
            })

        # Получаем первую страницу
        items, total = await user_repo.paginate(page=1, page_size=10)

        assert total == 25
        assert len(items) == 10

        # Получаем вторую страницу
        items2, total2 = await user_repo.paginate(page=2, page_size=10)

        assert total2 == 25
        assert len(items2) == 10
