"""
Unit-тесты ChannelSettingsRepo.
"""

from decimal import Decimal

import pytest


class TestChannelSettingsRepo:
    """Тесты ChannelSettingsRepo."""

    @pytest.mark.asyncio
    async def test_get_or_create_default_creates(
        self,
        channel_settings_repo,
        test_channel,
        owner_user,
    ):
        """Нет настроек → создаёт с defaults."""
        settings = await channel_settings_repo.get_or_create_default(
            channel_id=test_channel.id,
            owner_id=owner_user.id,
        )

        assert settings.price_per_post == Decimal("500.00")
        assert settings.auto_accept_enabled is False
        assert settings.channel_id == test_channel.id

    @pytest.mark.asyncio
    async def test_get_or_create_default_returns_existing(
        self,
        channel_settings_repo,
        test_channel,
        owner_user,
    ):
        """Настройки есть → возвращает существующие без изменений."""
        # Создаём настройки
        await channel_settings_repo.get_or_create_default(
            channel_id=test_channel.id,
            owner_id=owner_user.id,
        )

        # Получаем снова
        settings = await channel_settings_repo.get_or_create_default(
            channel_id=test_channel.id,
            owner_id=owner_user.id,
        )

        assert settings.price_per_post == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_upsert_partial(
        self,
        channel_settings_repo,
        test_channel,
        owner_user,
    ):
        """Upsert только цены → остальные поля не изменились."""
        # Создаём настройки
        await channel_settings_repo.get_or_create_default(
            channel_id=test_channel.id,
            owner_id=owner_user.id,
        )

        # Обновляем только цену
        settings = await channel_settings_repo.upsert(
            channel_id=test_channel.id,
            owner_id=owner_user.id,
            price_per_post=Decimal("1000.00"),
        )

        assert settings.price_per_post == Decimal("1000.00")
        assert settings.auto_accept_enabled is False  # не изменилось
