"""
Unit тесты уведомлений PlacementRequest.
Тестирует реальный API src/bot/handlers/shared/notifications.py
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.handlers.shared.notifications import (
    notify_advertiser_accepted,
    notify_advertiser_counter,
    notify_advertiser_published,
    notify_advertiser_rejected,
    notify_owner_new_request,
    notify_owner_post_completed,
    notify_payment_received,
)


def _make_bot() -> MagicMock:
    """Создать mock Bot с AsyncMock.send_message."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


# ---------------------------------------------------------------------------
# notify_owner_new_request
# ---------------------------------------------------------------------------


class TestNotifyOwnerNewRequest:
    """Тесты уведомления владельца о новой заявке."""

    @pytest.mark.asyncio
    async def test_sends_to_owner(self):
        """Сообщение отправляется на telegram_id владельца."""
        bot = _make_bot()
        await notify_owner_new_request(bot, owner_telegram_id=222, request_id=5)
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args
        assert call_kwargs.kwargs.get("chat_id") == 222 or call_kwargs.args[0] == 222

    @pytest.mark.asyncio
    async def test_text_contains_request_id(self):
        """Текст уведомления содержит ID заявки."""
        bot = _make_bot()
        await notify_owner_new_request(bot, owner_telegram_id=222, request_id=42)
        call_kwargs = bot.send_message.call_args
        text = call_kwargs.kwargs.get("text", "") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else "")
        assert "42" in text

    @pytest.mark.asyncio
    async def test_keyboard_has_review_button(self):
        """Клавиатура содержит кнопку просмотра заявки."""
        bot = _make_bot()
        await notify_owner_new_request(bot, owner_telegram_id=222, request_id=7)
        call_kwargs = bot.send_message.call_args
        markup = call_kwargs.kwargs.get("reply_markup")
        assert markup is not None
        buttons = [btn.callback_data for row in markup.inline_keyboard for btn in row]
        assert any("own:request:7" in b for b in buttons)

    @pytest.mark.asyncio
    async def test_exception_suppressed(self):
        """Исключение при отправке не пробрасывается наружу."""
        bot = _make_bot()
        bot.send_message.side_effect = Exception("Network error")
        # Should not raise
        await notify_owner_new_request(bot, owner_telegram_id=222, request_id=1)


# ---------------------------------------------------------------------------
# notify_advertiser_counter
# ---------------------------------------------------------------------------


class TestNotifyAdvertiserCounter:
    """Тесты уведомления о контр-предложении."""

    @pytest.mark.asyncio
    async def test_sends_to_advertiser(self):
        """Сообщение отправляется рекламодателю."""
        bot = _make_bot()
        await notify_advertiser_counter(
            bot,
            advertiser_telegram_id=111,
            request_id=1,
            channel_name="testchannel",
            counter_price=Decimal("800"),
            counter_schedule="01.04.2026 12:00",
            counter_round=1,
        )
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args
        assert call_kwargs.kwargs.get("chat_id") == 111 or call_kwargs.args[0] == 111

    @pytest.mark.asyncio
    async def test_text_contains_round_number(self):
        """Текст содержит номер раунда переговоров."""
        bot = _make_bot()
        await notify_advertiser_counter(
            bot,
            advertiser_telegram_id=111,
            request_id=1,
            channel_name="testchannel",
            counter_price=Decimal("800"),
            counter_schedule="01.04.2026 12:00",
            counter_round=2,
        )
        call_kwargs = bot.send_message.call_args
        text = call_kwargs.kwargs.get("text", "") or ""
        assert "2/3" in text

    @pytest.mark.asyncio
    async def test_text_contains_counter_price(self):
        """Текст содержит новую цену."""
        bot = _make_bot()
        await notify_advertiser_counter(
            bot,
            advertiser_telegram_id=111,
            request_id=1,
            channel_name="testchannel",
            counter_price=Decimal("950"),
            counter_schedule="01.04.2026 12:00",
            counter_round=1,
        )
        call_kwargs = bot.send_message.call_args
        text = call_kwargs.kwargs.get("text", "") or ""
        assert "950" in text

    @pytest.mark.asyncio
    async def test_round_3_no_counter_button(self):
        """На 3 раунде кнопки 'Контр-предложение' нет."""
        bot = _make_bot()
        await notify_advertiser_counter(
            bot,
            advertiser_telegram_id=111,
            request_id=1,
            channel_name="testchannel",
            counter_price=Decimal("800"),
            counter_schedule="01.04.2026 12:00",
            counter_round=3,
        )
        call_kwargs = bot.send_message.call_args
        markup = call_kwargs.kwargs.get("reply_markup")
        if markup:
            buttons_cb = [btn.callback_data for row in markup.inline_keyboard for btn in row]
            assert not any("camp:counter:reply" in b for b in buttons_cb)


# ---------------------------------------------------------------------------
# notify_advertiser_accepted
# ---------------------------------------------------------------------------


class TestNotifyAdvertiserAccepted:
    """Тесты уведомления о принятии заявки."""

    @pytest.mark.asyncio
    async def test_sends_to_advertiser(self):
        """Сообщение отправляется рекламодателю."""
        bot = _make_bot()
        await notify_advertiser_accepted(
            bot,
            advertiser_telegram_id=111,
            request_id=1,
            channel_name="testchannel",
            format_name="Пост 24ч",
            final_price=Decimal("500"),
            final_schedule="01.04.2026 12:00",
        )
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyboard_has_pay_button(self):
        """Клавиатура содержит кнопку оплаты."""
        bot = _make_bot()
        await notify_advertiser_accepted(
            bot,
            advertiser_telegram_id=111,
            request_id=5,
            channel_name="testchannel",
            format_name="Пост 24ч",
            final_price=Decimal("500"),
            final_schedule="01.04.2026 12:00",
        )
        call_kwargs = bot.send_message.call_args
        markup = call_kwargs.kwargs.get("reply_markup")
        assert markup is not None
        buttons_cb = [btn.callback_data for row in markup.inline_keyboard for btn in row]
        assert any("camp:pay:5" in b for b in buttons_cb)

    @pytest.mark.asyncio
    async def test_text_contains_price(self):
        """Текст содержит итоговую цену."""
        bot = _make_bot()
        await notify_advertiser_accepted(
            bot,
            advertiser_telegram_id=111,
            request_id=1,
            channel_name="testchannel",
            format_name="Пост 24ч",
            final_price=Decimal("750"),
            final_schedule="01.04.2026 12:00",
        )
        call_kwargs = bot.send_message.call_args
        text = call_kwargs.kwargs.get("text", "") or ""
        assert "750" in text


# ---------------------------------------------------------------------------
# notify_advertiser_rejected
# ---------------------------------------------------------------------------


class TestNotifyAdvertiserRejected:
    """Тесты уведомления об отклонении."""

    @pytest.mark.asyncio
    async def test_sends_to_advertiser(self):
        """Уведомление отправляется рекламодателю."""
        bot = _make_bot()
        await notify_advertiser_rejected(
            bot, advertiser_telegram_id=111, request_id=1, channel_name="testchannel"
        )
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_contains_request_id(self):
        """Текст содержит ID заявки."""
        bot = _make_bot()
        await notify_advertiser_rejected(
            bot, advertiser_telegram_id=111, request_id=99, channel_name="testchannel"
        )
        call_kwargs = bot.send_message.call_args
        text = call_kwargs.kwargs.get("text", "") or ""
        assert "99" in text


# ---------------------------------------------------------------------------
# notify_advertiser_published
# ---------------------------------------------------------------------------


class TestNotifyAdvertiserPublished:
    """Тесты уведомления о публикации."""

    @pytest.mark.asyncio
    async def test_sends_to_advertiser(self):
        """Уведомление отправляется рекламодателю."""
        bot = _make_bot()
        await notify_advertiser_published(
            bot, advertiser_telegram_id=111, placement_id=1, channel_name="testchannel"
        )
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_contains_placement_id(self):
        """Текст содержит ID размещения."""
        bot = _make_bot()
        await notify_advertiser_published(
            bot, advertiser_telegram_id=111, placement_id=77, channel_name="testchannel"
        )
        call_kwargs = bot.send_message.call_args
        text = call_kwargs.kwargs.get("text", "") or ""
        assert "77" in text


# ---------------------------------------------------------------------------
# notify_payment_received (alias → notify_owner_post_completed)
# ---------------------------------------------------------------------------


class TestNotifyPaymentReceived:
    """Тесты alias notify_payment_received."""

    @pytest.mark.asyncio
    async def test_sends_to_owner(self):
        """Уведомление отправляется владельцу канала."""
        bot = _make_bot()
        await notify_payment_received(
            bot, owner_telegram_id=222, earned_rub=Decimal("400"), channel_name="testchannel"
        )
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_contains_amount(self):
        """Текст содержит сумму выплаты."""
        bot = _make_bot()
        await notify_payment_received(
            bot, owner_telegram_id=222, earned_rub=Decimal("850"), channel_name="testchannel"
        )
        call_kwargs = bot.send_message.call_args
        text = call_kwargs.kwargs.get("text", "") or ""
        assert "850" in text


# ---------------------------------------------------------------------------
# Skipped — no implementation
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="notify_cancelled not implemented in notifications.py")
class TestNotifyCancelled:
    pass


@pytest.mark.skip(reason="notify_sla_expired not implemented in notifications.py")
class TestNotifySlaExpired:
    pass


@pytest.mark.skip(reason="private helpers _format_datetime, _format_owner_payout, _send_notification, _truncate_text not exposed")
class TestPrivateHelpers:
    pass
