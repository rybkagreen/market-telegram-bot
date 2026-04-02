"""
Тесты для AI Service.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.services.mistral_ai_service import MistralAIService as AIService


class TestAIServiceCache:
    """Тесты кэширования AI Service."""

    @pytest.fixture
    def ai_service(self) -> AIService:
        """Создать AIService."""
        return AIService()

    @pytest.mark.asyncio
    async def test_get_cache_key(self, ai_service: AIService) -> None:
        """Проверка генерации ключа кэша."""
        key1 = ai_service._get_cache_key("test prompt")
        key2 = ai_service._get_cache_key("test prompt")
        key3 = ai_service._get_cache_key("another prompt")

        assert key1 == key2
        assert key1.startswith("ai_cache:")
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_check_cache_miss(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка отсутствия в кэше."""
        mock_redis.get = AsyncMock(return_value=None)
        ai_service._redis = mock_redis

        result = await ai_service._check_cache("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_check_cache_hit(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка попадания в кэш."""
        mock_redis.get = AsyncMock(return_value="cached response")
        ai_service._redis = mock_redis

        result = await ai_service._check_cache("test_key")
        assert result == "cached response"

    @pytest.mark.asyncio
    async def test_set_cache(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка записи в кэш."""
        mock_redis.setex = AsyncMock()
        ai_service._redis = mock_redis

        await ai_service._set_cache("test_key", "test_value", ttl=7200)

        mock_redis.setex.assert_called_once_with("test_key", 7200, "test_value")


class TestAIServiceGeneration:
    """Тесты генерации текста AI Service."""

    @pytest.fixture
    def ai_service(self) -> AIService:
        """Создать AIService."""
        return AIService()

    @pytest.mark.asyncio
    async def test_generate_ad_text_cache_hit(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка генерации с попаданием в кэш."""
        mock_redis.get = AsyncMock(return_value="cached ad text")
        ai_service._redis = mock_redis

        # Мок deduct_balance
        with patch.object(ai_service, "_deduct_balance", new_callable=AsyncMock, return_value=True):
            result = await ai_service.generate_ad_text(
                user_id=1,
                description="Test product",
            )

        assert result == "cached ad text"

    @pytest.mark.asyncio
    async def test_generate_ad_text_insufficient_balance(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка недостаточного баланса."""
        mock_redis.get = AsyncMock(return_value=None)
        ai_service._redis = mock_redis

        with (
            patch.object(ai_service, "_deduct_balance", new_callable=AsyncMock, return_value=False),
            pytest.raises(ValueError, match="Insufficient balance"),
        ):
            await ai_service.generate_ad_text(
                user_id=1,
                description="Test product",
            )

    @pytest.mark.asyncio
    async def test_generate_ab_variants(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка генерации A/B вариантов."""
        mock_redis.get = AsyncMock(return_value=None)
        ai_service._redis = mock_redis

        # Мок _call_claude
        mock_response = "Variant 1\n---\nVariant 2\n---\nVariant 3"
        with (
            patch.object(
                ai_service, "_call_claude", new_callable=AsyncMock, return_value=mock_response
            ),
            patch.object(ai_service, "_deduct_balance", new_callable=AsyncMock, return_value=True),
        ):
            variants = await ai_service.generate_ab_variants(
                user_id=1,
                description="Test product",
                count=3,
            )

        assert len(variants) == 3
        assert variants[0] == "Variant 1"
        assert variants[1] == "Variant 2"
        assert variants[2] == "Variant 3"

    @pytest.mark.asyncio
    async def test_improve_text(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка улучшения текста."""
        mock_redis.get = AsyncMock(return_value=None)
        ai_service._redis = mock_redis

        with (
            patch.object(
                ai_service, "_call_claude", new_callable=AsyncMock, return_value="Improved text"
            ),
            patch.object(ai_service, "_deduct_balance", new_callable=AsyncMock, return_value=True),
        ):
            result = await ai_service.improve_text(
                user_id=1,
                original="Original text",
                improvement_type="more_engaging",
            )

        assert result == "Improved text"

    @pytest.mark.asyncio
    async def test_generate_hashtags(
        self,
        ai_service: AIService,
        mock_redis: MagicMock,
    ) -> None:
        """Проверка генерации хэштегов."""
        mock_redis.get = AsyncMock(return_value=None)
        ai_service._redis = mock_redis

        mock_response = "hashtag1, hashtag2, hashtag3, hashtag4, hashtag5"
        with (
            patch.object(
                ai_service, "_call_claude", new_callable=AsyncMock, return_value=mock_response
            ),
            patch.object(ai_service, "_deduct_balance", new_callable=AsyncMock, return_value=True),
        ):
            hashtags = await ai_service.generate_hashtags(
                user_id=1,
                text="Test text",
                count=5,
            )

        assert len(hashtags) == 5
        assert all(h.startswith("#") for h in hashtags)


class TestAIServiceDeductBalance:
    """Тесты списания баланса AI Service."""

    @pytest.fixture
    def ai_service(self) -> AIService:
        """Создать AIService."""
        return AIService()

    @pytest.mark.asyncio
    async def test_deduct_balance_success(
        self,
        ai_service: AIService,
    ) -> None:
        """Проверка успешного списания."""
        with patch("src.core.services.ai_service.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            mock_user_repo = MagicMock()
            mock_user = MagicMock()
            mock_user.balance = Decimal("100.00")
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo.update_balance = AsyncMock()

            with patch("src.core.services.ai_service.UserRepository", return_value=mock_user_repo):
                result = await ai_service._deduct_balance(user_id=1, amount=Decimal("10.00"))

        assert result is True
        mock_user_repo.update_balance.assert_called_once_with(1, Decimal("-10.00"))

    @pytest.mark.asyncio
    async def test_deduct_balance_user_not_found(
        self,
        ai_service: AIService,
    ) -> None:
        """Проверка отсутствия пользователя."""
        with patch("src.core.services.ai_service.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            mock_user_repo = MagicMock()
            mock_user_repo.get_by_id = AsyncMock(return_value=None)

            with patch("src.core.services.ai_service.UserRepository", return_value=mock_user_repo):
                result = await ai_service._deduct_balance(user_id=1, amount=Decimal("10.00"))

        assert result is False

    @pytest.mark.asyncio
    async def test_deduct_balance_insufficient(
        self,
        ai_service: AIService,
    ) -> None:
        """Проверка недостаточного баланса."""
        with patch("src.core.services.ai_service.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            mock_user_repo = MagicMock()
            mock_user = MagicMock()
            mock_user.balance = Decimal("5.00")
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

            with patch("src.core.services.ai_service.UserRepository", return_value=mock_user_repo):
                result = await ai_service._deduct_balance(user_id=1, amount=Decimal("10.00"))

        assert result is False
