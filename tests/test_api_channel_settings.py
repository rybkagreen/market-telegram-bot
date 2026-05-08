"""
Integration-тесты API /api/channel-settings/ (channel_id query param).
"""

import pytest


class TestAPIChannelSettings:
    """Тесты API channel_settings."""

    @pytest.mark.asyncio
    async def test_get_creates_defaults(
        self,
        api_client_with_owner_auth,
        test_channel,
        owner_user,
    ):
        """GET создаёт настройки с defaults если их нет."""
        response = await api_client_with_owner_auth.get(
            f"/api/channel-settings/?channel_id={test_channel.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["price_per_post"] == "1000.00"
        assert data["auto_accept_enabled"] is False

    @pytest.mark.asyncio
    async def test_patch_price(
        self,
        api_client_with_owner_auth,
        test_channel,
        owner_user,
    ):
        """PATCH обновляет цену."""
        # Сначала создаём настройки
        await api_client_with_owner_auth.get(f"/api/channel-settings/?channel_id={test_channel.id}")

        # Обновляем цену
        response = await api_client_with_owner_auth.patch(
            f"/api/channel-settings/?channel_id={test_channel.id}",
            json={"price_per_post": 1000},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["price_per_post"] == "1000.00"

    @pytest.mark.asyncio
    async def test_patch_invalid_price_422(
        self,
        api_client_with_owner_auth,
        test_channel,
        owner_user,
    ):
        """PATCH с ценой < 100 → 422."""
        response = await api_client_with_owner_auth.patch(
            f"/api/channel-settings/?channel_id={test_channel.id}",
            json={"price_per_post": 50},  # < 100
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_invalid_time_order_422(
        self,
        api_client_with_owner_auth,
        test_channel,
        owner_user,
    ):
        """PATCH с end_time < start_time → 422."""
        response = await api_client_with_owner_auth.patch(
            f"/api/channel-settings/?channel_id={test_channel.id}",
            json={"publish_start_time": "22:00", "publish_end_time": "09:00"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_partial_no_side_effects(
        self,
        api_client_with_owner_auth,
        test_channel,
        owner_user,
    ):
        """PATCH только auto_accept → остальные поля не изменились."""
        # Создаём настройки
        get_response = await api_client_with_owner_auth.get(
            f"/api/channel-settings/?channel_id={test_channel.id}"
        )
        original_price = get_response.json()["price_per_post"]

        # Обновляем только auto_accept
        response = await api_client_with_owner_auth.patch(
            f"/api/channel-settings/?channel_id={test_channel.id}",
            json={"auto_accept_enabled": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["auto_accept_enabled"] is True
        assert data["price_per_post"] == original_price  # не изменилось
