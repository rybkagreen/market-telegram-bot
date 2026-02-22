"""
Тесты для FastAPI API.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


class TestAuthRouter:
    """Тесты auth роутера."""

    @pytest.fixture
    def mock_validate_init_data(self):
        """Мок валидации initData."""
        with patch("src.api.routers.auth._validate_telegram_init_data") as mock:
            mock.return_value = {
                "user": '{"id": 123456789, "username": "testuser"}',
            }
            yield mock

    @pytest.fixture
    def mock_user_repo(self):
        """Мок UserRepository."""
        with patch("src.api.routers.auth.UserRepository") as mock:
            repo_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.telegram_id = 123456789
            repo_instance.get_by_telegram_id = AsyncMock(return_value=mock_user)
            repo_instance.create = AsyncMock(return_value=mock_user)
            mock.return_value.return_value = repo_instance
            yield mock

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        mock_validate_init_data,
        mock_user_repo,
    ):
        """Проверка успешного логина."""
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/login",
                json={"init_data": "test_init_data"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_init_data(self):
        """Проверка невалидного initData."""
        from src.api.main import app

        with patch(
            "src.api.routers.auth._validate_telegram_init_data", return_value=None
        ):
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/auth/login",
                    json={"init_data": "invalid_data"},
                )

        assert response.status_code == 401
        assert "Invalid initData" in response.json()["detail"]


class TestCampaignsRouter:
    """Тесты campaigns роутера."""

    @pytest.fixture
    def mock_get_current_user(self):
        """Мок get_current_user."""
        user = MagicMock()
        user.id = 1
        user.telegram_id = 123456789
        with patch("src.api.routers.campaigns.get_current_user", return_value=user):
            yield user

    @pytest.mark.asyncio
    async def test_create_campaign(self, mock_get_current_user):
        """Проверка создания кампании."""
        from src.api.main import app

        with patch("src.api.routers.campaigns.CampaignRepository") as mock_repo:
            repo_instance = MagicMock()
            mock_campaign = MagicMock()
            mock_campaign.id = 1
            mock_campaign.title = "Test Campaign"
            mock_campaign.status = "draft"
            repo_instance.create = AsyncMock(return_value=mock_campaign)
            mock_repo.return_value = repo_instance

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/campaigns",
                    json={
                        "title": "Test Campaign",
                        "text": "Test ad text",
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Campaign"

    @pytest.mark.asyncio
    async def test_get_campaigns(self, mock_get_current_user):
        """Проверка получения списка кампаний."""
        from src.api.main import app

        with patch("src.api.routers.campaigns.CampaignRepository") as mock_repo:
            repo_instance = MagicMock()
            mock_campaign = MagicMock()
            mock_campaign.id = 1
            mock_campaign.title = "Test"
            repo_instance.get_by_user = AsyncMock(return_value=([mock_campaign], 1))
            mock_repo.return_value = repo_instance

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/api/campaigns")

        assert response.status_code == 200
        data = response.json()
        assert "campaigns" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, mock_get_current_user):
        """Проверка отсутствия кампании."""
        from src.api.main import app

        with patch("src.api.routers.campaigns.CampaignRepository") as mock_repo:
            repo_instance = MagicMock()
            repo_instance.get_by_id = AsyncMock(return_value=None)
            mock_repo.return_value = repo_instance

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/api/campaigns/999")

        assert response.status_code == 404


class TestAnalyticsRouter:
    """Тесты analytics роутера."""

    @pytest.fixture
    def mock_get_current_user(self):
        """Мок get_current_user."""
        user = MagicMock()
        user.id = 1
        user.telegram_id = 123456789
        with patch("src.api.routers.analytics.get_current_user", return_value=user):
            yield user

    @pytest.mark.asyncio
    async def test_get_campaign_stats(self, mock_get_current_user):
        """Проверка получения статистики кампании."""
        from src.api.main import app

        with patch("src.api.routers.analytics.CampaignRepository") as mock_campaign:
            with patch("src.api.routers.analytics.analytics_service") as mock_service:
                campaign_repo_instance = MagicMock()
                mock_campaign_instance = MagicMock()
                mock_campaign_instance.user_id = 1
                campaign_repo_instance.get_by_id = AsyncMock(
                    return_value=mock_campaign_instance
                )
                mock_campaign.return_value = campaign_repo_instance

                mock_stats = MagicMock()
                mock_stats.total_sent = 100
                mock_stats.total_failed = 5
                mock_stats.total_skipped = 10
                mock_stats.total_pending = 0
                mock_stats.success_rate = 90.5
                mock_stats.total_cost = 500.0
                mock_stats.reach_estimate = 10000
                mock_service.get_campaign_stats = AsyncMock(return_value=mock_stats)

                async with AsyncClient(app=app, base_url="http://test") as ac:
                    response = await ac.get("/api/analytics/campaign/1")

        assert response.status_code == 200
        data = response.json()
        assert data["total_sent"] == 100
        assert data["success_rate"] == 90.5

    @pytest.mark.asyncio
    async def test_get_user_summary(self, mock_get_current_user):
        """Проверка получения сводки пользователя."""
        from src.api.main import app

        with patch("src.api.routers.analytics.analytics_service") as mock_service:
            mock_summary = MagicMock()
            mock_summary.total_campaigns = 10
            mock_summary.active_campaigns = 2
            mock_summary.completed_campaigns = 5
            mock_summary.total_spent = 5000.0
            mock_summary.avg_success_rate = 85.0
            mock_summary.total_chats_reached = 500
            mock_service.get_user_summary = AsyncMock(return_value=mock_summary)

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.get("/api/analytics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_campaigns"] == 10


class TestBillingRouter:
    """Тесты billing роутера."""

    @pytest.fixture
    def mock_get_current_user(self):
        """Мок get_current_user."""
        user = MagicMock()
        user.id = 1
        user.telegram_id = 123456789
        user.balance = 1000.0
        with patch("src.api.routers.billing.get_current_user", return_value=user):
            yield user

    @pytest.mark.asyncio
    async def test_get_balance(self, mock_get_current_user):
        """Проверка получения баланса."""
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/api/billing/balance")

        assert response.status_code == 200
        data = response.json()
        assert data["balance"] == "1000.0"
        assert data["currency"] == "RUB"

    @pytest.mark.asyncio
    async def test_create_topup(self, mock_get_current_user):
        """Проверка создания пополнения."""
        from src.api.main import app

        with patch("src.api.routers.billing.billing_service") as mock_service:
            mock_service.create_payment = AsyncMock(
                return_value={
                    "payment_id": "pay_123",
                    "payment_url": "https://yookassa.ru/payment/pay_123",
                    "amount": "500",
                    "status": "pending",
                }
            )

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/billing/topup",
                    json={"amount": 500, "payment_method": "yookassa"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == "pay_123"
        assert "payment_url" in data

    @pytest.mark.asyncio
    async def test_spend_balance_success(self, mock_get_current_user):
        """Проверка списания баланса (успех)."""
        from src.api.main import app

        with patch("src.api.routers.billing.UserRepository") as mock_user_repo:
            with patch("src.api.routers.billing.billing_service") as mock_service:
                user_repo_instance = MagicMock()
                mock_user = MagicMock()
                mock_user.balance = 1000.0
                user_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
                mock_user_repo.return_value = user_repo_instance

                mock_service.deduct_balance = AsyncMock()

                async with AsyncClient(app=app, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/billing/spend",
                        params={"amount": 100, "description": "Test spend"},
                    )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_spend_balance_insufficient(self, mock_get_current_user):
        """Проверка списания баланса (недостаточно средств)."""
        from src.api.main import app

        with patch("src.api.routers.billing.UserRepository") as mock_user_repo:
            user_repo_instance = MagicMock()
            mock_user = MagicMock()
            mock_user.balance = 50.0  # Меньше чем нужно списать
            user_repo_instance.get_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo.return_value = user_repo_instance

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/billing/spend",
                    params={"amount": 100, "description": "Test spend"},
                )

        assert response.status_code == 402  # Payment Required


class TestHealthEndpoint:
    """Тесты health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Проверка health endpoint."""
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Проверка корневого endpoint."""
        from src.api.main import app

        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "Market Telegram Bot API" in data["message"]
        assert data["docs"] == "/docs"
