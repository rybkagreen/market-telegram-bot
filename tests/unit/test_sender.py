"""
Тесты для Telegram Sender.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.utils.telegram.sender import (
    TelegramSender,
    SendResult,
    SendStatus,
    create_sender,
)


class TestSendResult:
    """Тесты SendResult dataclass."""

    def test_send_result_sent(self) -> None:
        """Проверка успешной отправки."""
        result = SendResult(
            status=SendStatus.SENT,
            message_id=123,
        )
        assert result.status == SendStatus.SENT
        assert result.message_id == 123
        assert result.error_message is None
        assert result.retry_after is None

    def test_send_result_failed(self) -> None:
        """Проверка неудачной отправки."""
        result = SendResult(
            status=SendStatus.FAILED,
            error_message="Bot forbidden",
        )
        assert result.status == SendStatus.FAILED
        assert result.message_id is None
        assert result.error_message == "Bot forbidden"

    def test_send_result_retry(self) -> None:
        """Проверка повторной попытки."""
        result = SendResult(
            status=SendStatus.RETRY,
            retry_after=60,
            error_message="FloodWait",
        )
        assert result.status == SendStatus.RETRY
        assert result.retry_after == 60


class TestTelegramSenderSuccess:
    """Тесты успешной отправки."""

    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Создать мок бота."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def sender(self, mock_bot: MagicMock) -> TelegramSender:
        """Создать TelegramSender."""
        return TelegramSender(mock_bot)

    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        sender: TelegramSender,
        mock_bot: MagicMock,
    ) -> None:
        """Проверка успешной отправки."""
        mock_message = MagicMock()
        mock_message.message_id = 456
        mock_bot.send_message.return_value = mock_message

        result = await sender.send_message(
            chat_id=123,
            text="Test message",
        )

        assert result.status == SendStatus.SENT
        assert result.message_id == 456
        mock_bot.send_message.assert_called_once_with(
            chat_id=123,
            text="Test message",
            parse_mode="HTML",
            disable_notification=False,
        )

    @pytest.mark.asyncio
    async def test_send_message_custom_parse_mode(
        self,
        sender: TelegramSender,
        mock_bot: MagicMock,
    ) -> None:
        """Проверка отправки с кастомным parse_mode."""
        mock_message = MagicMock()
        mock_message.message_id = 789
        mock_bot.send_message.return_value = mock_message

        await sender.send_message(
            chat_id=123,
            text="Test message",
            parse_mode="Markdown",
            disable_notification=True,
        )

        mock_bot.send_message.assert_called_once_with(
            chat_id=123,
            text="Test message",
            parse_mode="Markdown",
            disable_notification=True,
        )


class TestTelegramSenderErrors:
    """Тесты обработки ошибок."""

    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Создать мок бота."""
        bot = MagicMock()
        return bot

    @pytest.fixture
    def sender(self, mock_bot: MagicMock) -> TelegramSender:
        """Создать TelegramSender."""
        return TelegramSender(mock_bot)

    @pytest.mark.asyncio
    async def test_send_message_flood_wait(
        self,
        sender: TelegramSender,
        mock_bot: MagicMock,
    ) -> None:
        """Проверка обработки FloodWait."""
        from aiogram.exceptions import TelegramRetryAfter

        mock_bot.send_message = AsyncMock(
            side_effect=TelegramRetryAfter(
                method="send_message",
                message="FloodWait",
                retry_after=30,
            )
        )

        result = await sender.send_message(
            chat_id=123,
            text="Test message",
        )

        assert result.status == SendStatus.RETRY
        assert result.retry_after is not None
        assert result.retry_after >= 30

    @pytest.mark.asyncio
    async def test_send_message_forbidden(
        self,
        sender: TelegramSender,
        mock_bot: MagicMock,
    ) -> None:
        """Проверка обработки ForbiddenError."""
        from aiogram.exceptions import TelegramForbiddenError

        mock_bot.send_message = AsyncMock(
            side_effect=TelegramForbiddenError(
                method="send_message",
                message="Bot forbidden",
            )
        )

        result = await sender.send_message(
            chat_id=123,
            text="Test message",
        )

        assert result.status == SendStatus.FAILED
        assert "forbidden" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_send_message_migrate_to_chat(
        self,
        sender: TelegramSender,
        mock_bot: MagicMock,
    ) -> None:
        """Проверка обработки MigrateToChat."""
        from aiogram.exceptions import TelegramMigrateToChat

        mock_bot.send_message = AsyncMock(
            side_effect=TelegramMigrateToChat(
                method="send_message",
                message="Migrated",
                migrate_to_chat_id=-987654321,
            )
        )

        result = await sender.send_message(
            chat_id=123,
            text="Test message",
        )

        assert result.status == SendStatus.RETRY
        assert "migrated" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_send_message_all_retries_failed(
        self,
        sender: TelegramSender,
        mock_bot: MagicMock,
    ) -> None:
        """Проверка исчерпания всех попыток."""
        mock_bot.send_message = AsyncMock(
            side_effect=Exception("Unknown error")
        )

        result = await sender.send_message(
            chat_id=123,
            text="Test message",
        )

        assert result.status == SendStatus.FAILED
        assert mock_bot.send_message.call_count == 3  # max_retries

    @pytest.mark.asyncio
    async def test_send_message_safe_no_exception(
        self,
        sender: TelegramSender,
        mock_bot: MagicMock,
    ) -> None:
        """Проверка безопасной отправки без исключений."""
        mock_bot.send_message = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        result = await sender.send_message_safe(
            chat_id=123,
            text="Test message",
        )

        assert result.status == SendStatus.FAILED
        assert "Unexpected" in result.error_message


class TestCreateSender:
    """Тесты создания sender."""

    @pytest.mark.asyncio
    async def test_create_sender(self) -> None:
        """Проверка создания TelegramSender."""
        with patch("src.utils.telegram.sender.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.session = AsyncMock()
            mock_bot.session.close = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = await create_sender("test_token")

            assert isinstance(sender, TelegramSender)
            assert sender.bot == mock_bot
            mock_bot_class.assert_called_once_with(token="test_token")

    @pytest.mark.asyncio
    async def test_sender_close(self) -> None:
        """Проверка закрытия sender."""
        with patch("src.utils.telegram.sender.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.session = AsyncMock()
            mock_bot.session.close = AsyncMock()
            mock_bot_class.return_value = mock_bot

            sender = await create_sender("test_token")
            await sender.close()

            mock_bot.session.close.assert_called_once()
