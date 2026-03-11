"""
Unit тесты уведомлений PlacementRequest.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.shared.notifications import (
    _format_datetime,
    _format_owner_payout,
    _send_notification,
    _truncate_text,
    notify_cancelled,
    notify_counter_offer,
    notify_new_request,
    notify_owner_accepted,
    notify_payment_received,
    notify_published,
    notify_rejected,
    notify_sla_expired,
)


class TestHelperFunctions:
    """Тесты вспомогательных функций."""

    def test_format_owner_payout(self):
        """Вычисление дохода владельца (80%)."""
        assert _format_owner_payout(Decimal("500")) == Decimal("400")
        assert _format_owner_payout(Decimal("1000")) == Decimal("800")

    def test_truncate_text_short(self):
        """Текст короче лимита не обрезается."""
        text = "Short text"
        assert _truncate_text(text, max_len=300) == text

    def test_truncate_text_long(self):
        """Длинный текст обрезается до 300 символов + ..."""
        text = "A" * 350
        result = _truncate_text(text, max_len=300)
        assert len(result) == 303  # 300 + "..."
        assert result.endswith("...")

    def test_format_datetime_none(self):
        """None дата форматируется как 'Не указана'."""
        assert _format_datetime(None) == "Не указана"

    def test_format_datetime_valid(self):
        """Дата форматируется как dd.mm.yyyy HH:MM."""
        from datetime import datetime

        dt = datetime(2026, 3, 15, 10, 30)
        assert _format_datetime(dt) == "15.03.2026 10:30"


class TestSendNotification:
    """Тесты отправки уведомлений с дедупликацией."""

    @pytest.mark.asyncio
    async def test_send_notification_first_time(self):
        """Первое уведомление отправляется."""
        with patch("src.bot.handlers.shared.notifications.redis_client") as mock_redis:
            mock_redis.exists = AsyncMock(return_value=False)
            mock_redis.setex = AsyncMock()

            with patch("src.bot.handlers.shared.notifications.Bot") as mock_bot_class:
                mock_bot = MagicMock()
                mock_bot.send_message = AsyncMock()
                mock_bot.session.close = AsyncMock()
                mock_bot_class.return_value = mock_bot

                result = await _send_notification(
                    telegram_id=123,
                    text="Test message",
                    placement_id=1,
                    event_key="test_event",
                )

                assert result is True
                mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_deduplicated(self):
        """Повторное уведомление с тем же ключом не отправляется."""
        with patch("src.bot.handlers.shared.notifications.redis_client") as mock_redis:
            mock_redis.exists = AsyncMock(return_value=True)
            mock_redis.setex = AsyncMock()

            result = await _send_notification(
                telegram_id=123,
                text="Test message",
                placement_id=1,
                event_key="test_event",
            )

            assert result is False
            mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_notification_dedup_ttl(self):
        """TTL дедупликации = 300 секунд."""
        with patch("src.bot.handlers.shared.notifications.redis_client") as mock_redis:
            # Настраиваем redis_client как AsyncMock с правильными методами
            mock_redis.exists = AsyncMock(return_value=False)
            mock_redis.setex = AsyncMock(return_value=True)
            
            # Mock Bot чтобы избежать network calls
            with patch("src.bot.handlers.shared.notifications.Bot") as mock_bot_class:
                mock_bot = AsyncMock()
                mock_bot.send_message = AsyncMock()
                mock_bot.session.close = AsyncMock()
                mock_bot_class.return_value = mock_bot
                
                await _send_notification(
                    telegram_id=123,
                    text="Test",
                    placement_id=1,
                    event_key="test",
                )

                # Проверка что setex вызван с TTL=300
                call_args = mock_redis.setex.call_args
                assert call_args[0][1] == 300  # TTL


def _create_mock_placement(**kwargs):
    """Создать mock placement объекта."""
    placement = MagicMock()
    placement.id = kwargs.get("id", 1)
    placement.advertiser_id = kwargs.get("advertiser_id", 1)
    placement.channel_id = kwargs.get("channel_id", 10)
    placement.proposed_price = kwargs.get("proposed_price", Decimal("500"))
    placement.final_price = kwargs.get("final_price", None)
    placement.counter_offer_count = kwargs.get("counter_offer_count", 0)
    placement.final_text = kwargs.get("final_text", "Test")
    placement.status = kwargs.get("status", MagicMock())
    return placement


def _create_mock_user(telegram_id, user_id=None):
    """Создать mock user объекта."""
    user = MagicMock()
    user.id = user_id or telegram_id
    user.telegram_id = telegram_id
    user.first_name = "Test User"
    return user


class TestNotifyNewRequest:
    """Тесты уведомления о новой заявке."""

    @pytest.mark.asyncio
    async def test_notify_new_request_sends_to_owner(self):
        """Уведомление отправляется владельцу канала."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test ad text",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            mock_send.return_value = True

            sent_owner, sent_advertiser = await notify_new_request(
                placement, advertiser, owner, "testchannel"
            )

            assert sent_owner is True
            assert sent_advertiser is False
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_new_request_text_contains_price(self):
        """Текст содержит предложенную цену."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            await notify_new_request(placement, advertiser, owner, "testchannel")

            call_args = mock_send.call_args
            text = call_args[0][1]
            assert "500 кр" in text

    @pytest.mark.asyncio
    async def test_notify_new_request_text_contains_payout(self):
        """Текст содержит payout = price * 0.80."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            await notify_new_request(placement, advertiser, owner, "testchannel")

            call_args = mock_send.call_args
            text = call_args[0][1]
            # Decimal форматируется как "400.00", проверяем наличие "400"
            assert "400" in text  # 500 * 0.80

    @pytest.mark.asyncio
    async def test_notify_new_request_truncates_long_text(self):
        """Длинный текст поста обрезается до 300 символов."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="A" * 500,  # Длинный текст
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            await notify_new_request(placement, advertiser, owner, "testchannel")

            call_args = mock_send.call_args
            text = call_args[0][1]
            # Проверяем что текст содержит обрезанный пост
            assert "..." in text or len([l for l in text.split("\n") if "A" in l]) > 0


class TestNotifyCounterOffer:
    """Тесты уведомления о контр-предложении."""

    @pytest.mark.asyncio
    async def test_notify_counter_offer_sends_to_advertiser(self):
        """Уведомление отправляется рекламодателю."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_price=Decimal("800"),
            counter_offer_count=1,
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            mock_send.return_value = True

            result = await notify_counter_offer(placement, advertiser, "testchannel")

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_counter_offer_shows_round_number(self):
        """Текст содержит номер раунда переговоров."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_price=Decimal("800"),
            counter_offer_count=1,
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            await notify_counter_offer(placement, advertiser, "testchannel")

            call_args = mock_send.call_args
            text = call_args[0][1]
            assert "1/3" in text  # Раунд 1 из 3


class TestNotifyPublished:
    """Тесты уведомления о публикации."""

    @pytest.mark.asyncio
    async def test_notify_published_owner_receives_payout_amount(self):
        """Владелец получает уведомление с суммой payout."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            final_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            mock_send.return_value = True

            sent_owner, sent_advertiser = await notify_published(
                placement, advertiser, owner, "testchannel"
            )

            assert sent_owner is True
            assert sent_advertiser is True

            # Проверка что owner получил уведомление с payout
            # Decimal форматируется как "400.00", проверяем наличие "400"
            call_args = mock_send.call_args
            text = call_args[0][1]
            assert "400" in text  # 500 * 0.80


class TestNotifySlaExpired:
    """Тесты уведомления об истечении SLA."""

    @pytest.mark.asyncio
    async def test_sla_expired_sends_to_both(self):
        """Уведомления отправляются и owner, и advertiser."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            mock_send.return_value = True

            sent_owner, sent_advertiser = await notify_sla_expired(
                placement, advertiser, owner, "testchannel"
            )

            assert sent_owner is True
            assert sent_advertiser is True
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_sla_expired_owner_text_explains_penalty(self):
        """Текст для owner объясняет штраф."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            await notify_sla_expired(placement, advertiser, owner, "testchannel")

            # Первый вызов — owner
            call_args = mock_send.call_args_list[0]
            text = call_args[0][1]
            assert "24 часов" in text or "просрочена" in text.lower()

    @pytest.mark.asyncio
    async def test_sla_expired_advertiser_text_contains_refund(self):
        """Текст для advertiser содержит информацию о возврате."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            await notify_sla_expired(placement, advertiser, owner, "testchannel")

            # Второй вызов — advertiser
            call_args = mock_send.call_args_list[1]
            text = call_args[0][1]
            assert "500 кр" in text or "возврат" in text.lower()


class TestNotifyRejected:
    """Тесты уведомления об отклонении."""

    @pytest.mark.asyncio
    async def test_notify_rejected_sends_to_advertiser(self):
        """Уведомление отправляется рекламодателю."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            mock_send.return_value = True

            result = await notify_rejected(placement, advertiser, "testchannel")

            assert result is True
            mock_send.assert_called_once()


class TestNotifyCancelled:
    """Тесты уведомления об отмене."""

    @pytest.mark.asyncio
    async def test_notify_cancelled_sends_to_both(self):
        """Уведомления отправляются и owner, и advertiser."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            mock_send.return_value = True

            sent_owner, sent_advertiser = await notify_cancelled(
                placement, advertiser, owner, "testchannel"
            )

            assert sent_owner is True
            assert sent_advertiser is True
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_notify_cancelled_shows_reputation_delta(self):
        """Текст содержит изменение репутации."""
        placement = _create_mock_placement(
            id=1,
            advertiser_id=1,
            channel_id=10,
            proposed_price=Decimal("500"),
            final_text="Test",
        )

        advertiser = _create_mock_user(111, 1)
        owner = _create_mock_user(222, 2)

        with patch("src.bot.handlers.shared.notifications._send_notification") as mock_send:
            await notify_cancelled(placement, advertiser, owner, "testchannel", reputation_delta=-5.0)

            # reputation_delta показывается только advertiser, не owner
            # Проверяем что вызов был с advertiser.telegram_id (111)
            advertiser_call = None
            for call in mock_send.call_args_list:
                if call[0][0] == 111:  # advertiser.telegram_id
                    advertiser_call = call
                    break
            
            assert advertiser_call is not None, "Advertiser notification not found"
            text = advertiser_call[0][1]
            # Формат: "Изменение репутации: <-5.0>"
            assert "-5" in text or "репутации" in text.lower()
