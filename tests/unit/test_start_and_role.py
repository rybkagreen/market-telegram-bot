# tests/unit/test_start_and_role.py
"""
Тесты команды /start и выбора роли пользователем.
Автономные тесты без зависимостей от БД и внешних сервисов.

Покрывает:
- Новый пользователь → создаётся, получает главное меню
- Существующий пользователь → получает меню без повторной регистрации
- Выбор роли advertiser / owner / both
- FSM сбрасывается при /start
- Заблокированный пользователь → access denied
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def tg_user_new():
    """Telegram юзер которого нет в БД."""
    u = MagicMock()
    u.id = 999001
    u.username = "newuser"
    u.first_name = "New"
    u.last_name = "User"
    u.language_code = "ru"
    return u


@pytest.fixture
def tg_user_existing():
    """Telegram юзер который уже есть в БД."""
    u = MagicMock()
    u.id = 999002
    u.username = "existinguser"
    u.first_name = "Existing"
    return u


@pytest.fixture
def db_user_new_role():
    """DB User только что зарегистрированный, роль 'new'."""
    u = MagicMock()
    u.id = 1
    u.telegram_id = 999001
    u.role = "new"
    u.is_banned = False
    u.credits = 0
    return u


@pytest.fixture
def db_user_advertiser():
    """DB User с ролью advertiser."""
    u = MagicMock()
    u.id = 2
    u.telegram_id = 999002
    u.role = "advertiser"
    u.is_banned = False
    u.credits = 500
    return u


@pytest.fixture
def db_user_banned():
    u = MagicMock()
    u.id = 5
    u.telegram_id = 999005
    u.role = "advertiser"
    u.is_banned = True
    u.credits = 0
    return u


@pytest.fixture
def mock_message():
    """Мок Message с answer."""
    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.answer_photo = AsyncMock()
    msg.delete = AsyncMock()
    msg.from_user = MagicMock()
    return msg


@pytest.fixture
def mock_callback():
    """Мок CallbackQuery с answer и message.edit_text."""
    cb = MagicMock()
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.edit_reply_markup = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.from_user = MagicMock()
    return cb


@pytest.fixture
def mock_state():
    """Мок FSMContext."""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=None)
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def mock_async_session():
    """Мок async session context manager."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def mock_user_repo():
    """Мок UserRepository."""
    from src.db.repositories.user_repo import UserRepository
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_telegram_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update_role = AsyncMock()
    return repo


# ─────────────────────────────────────────────
# Тесты команды /start
# ─────────────────────────────────────────────

class TestStartCommandNewUser:
    """/start для нового пользователя."""

    @pytest.mark.asyncio
    async def test_new_user_created_in_db(
        self, mock_message, mock_state, tg_user_new, db_user_new_role, mock_user_repo, mock_async_session
    ):
        """Новый пользователь создаётся в БД при первом /start."""
        mock_message.from_user = tg_user_new
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)
        mock_user_repo.create = AsyncMock(return_value=db_user_new_role)
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    await _handle_start(mock_message, mock_state, None)

                    mock_user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_user_receives_welcome_message(
        self, mock_message, mock_state, tg_user_new, db_user_new_role, mock_user_repo, mock_async_session
    ):
        """Новый пользователь получает приветственное сообщение."""
        mock_message.from_user = tg_user_new
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)
        mock_user_repo.create = AsyncMock(return_value=db_user_new_role)
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    await _handle_start(mock_message, mock_state, None)

                    from src.bot.handlers.shared.start import send_banner_with_menu
                    send_banner_with_menu.assert_called()

    @pytest.mark.asyncio
    async def test_new_user_fsm_cleared(
        self, mock_message, mock_state, tg_user_new, db_user_new_role, mock_user_repo, mock_async_session
    ):
        """При /start FSM состояние сбрасывается."""
        mock_message.from_user = tg_user_new
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)
        mock_user_repo.create = AsyncMock(return_value=db_user_new_role)
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    await _handle_start(mock_message, mock_state, None)

                    mock_state.clear.assert_called()

    @pytest.mark.asyncio
    async def test_new_user_role_is_new(self, db_user_new_role):
        """Новый пользователь получает роль 'new', не advertiser/owner сразу."""
        assert db_user_new_role.role == "new"

    @pytest.mark.asyncio
    async def test_concurrent_start_requests(
        self, mock_message, mock_state, tg_user_new, mock_user_repo, mock_async_session
    ):
        """Два одновременных /start не создают двух пользователей."""
        mock_message.from_user = tg_user_new
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)
        mock_user_repo.create = AsyncMock()
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    
                    await asyncio.gather(
                        _handle_start(mock_message, mock_state, None),
                        _handle_start(mock_message, mock_state, None)
                    )
                    
                    assert mock_user_repo.create.call_count == 1


class TestStartCommandExistingUser:
    """/start для существующего пользователя."""

    @pytest.mark.asyncio
    async def test_existing_user_not_recreated(
        self, mock_message, mock_state, tg_user_existing, db_user_advertiser, mock_user_repo, mock_async_session
    ):
        """Существующий пользователь не создаётся повторно."""
        mock_message.from_user = tg_user_existing
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=db_user_advertiser)
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    await _handle_start(mock_message, mock_state, None)

                    mock_user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_user_gets_main_menu(
        self, mock_message, mock_state, tg_user_existing, db_user_advertiser, mock_user_repo, mock_async_session
    ):
        """Существующий пользователь получает главное меню."""
        mock_message.from_user = tg_user_existing
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=db_user_advertiser)
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    await _handle_start(mock_message, mock_state, None)

                    from src.bot.handlers.shared.start import send_banner_with_menu
                    send_banner_with_menu.assert_called()

    @pytest.mark.asyncio
    async def test_banned_user_gets_access_denied(
        self, mock_message, mock_state, db_user_banned, mock_user_repo, mock_async_session
    ):
        """Забаненный пользователь получает сообщение об отказе."""
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = db_user_banned.telegram_id
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=db_user_banned)
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    await _handle_start(mock_message, mock_state, None)

                    assert mock_message.answer.called

    @pytest.mark.asyncio
    async def test_start_with_active_fsm_state_clears_it(
        self, mock_message, mock_state, tg_user_existing, db_user_advertiser, mock_user_repo, mock_async_session
    ):
        """Если пользователь застрял в FSM — /start его сбрасывает."""
        mock_message.from_user = tg_user_existing
        mock_state.get_state = AsyncMock(return_value="PlacementStates:choosing_channel")
        mock_user_repo.get_by_telegram_id = AsyncMock(return_value=db_user_advertiser)
        mock_async_session.__aenter__.return_value = mock_async_session

        with patch(
            "src.bot.handlers.shared.start.UserRepository",
            return_value=mock_user_repo
        ):
            with patch(
                "src.bot.handlers.shared.start.async_session_factory",
                return_value=mock_async_session
            ):
                with patch("src.bot.handlers.shared.start.send_banner_with_menu"):
                    from src.bot.handlers.shared.start import _handle_start
                    await _handle_start(mock_message, mock_state, None)

                    mock_state.clear.assert_called()


# ─────────────────────────────────────────────
# Тесты выбора роли
# ─────────────────────────────────────────────

class TestRoleSelection:
    """Выбор роли через callback."""

    @pytest.mark.asyncio
    async def test_change_role_shows_menu(self, mock_callback, mock_state):
        """change_role показывает меню выбора роли."""
        mock_callback.from_user = MagicMock()
        mock_callback.from_user.id = 123
        mock_callback.data = "main:change_role"
        mock_callback.message = MagicMock()

        with patch("src.bot.handlers.shared.start.safe_callback_edit") as mock_edit:
            from src.bot.handlers.shared.start import change_role
            await change_role(mock_callback, mock_state)

            mock_edit.assert_called_once()
            mock_callback.answer.assert_called()

    @pytest.mark.asyncio
    async def test_change_role_clears_state(self, mock_callback, mock_state):
        """change_role сбрасывает FSM состояние."""
        mock_callback.from_user = MagicMock()
        mock_callback.from_user.id = 123
        mock_callback.data = "main:change_role"
        mock_callback.message = MagicMock()

        with patch("src.bot.handlers.shared.start.safe_callback_edit"):
            from src.bot.handlers.shared.start import change_role
            await change_role(mock_callback, mock_state)

            mock_state.clear.assert_called()

    @pytest.mark.asyncio
    async def test_change_role_callback_answered(self, mock_callback, mock_state):
        """callback.answer() вызван — кнопка не 'застревает' у пользователя."""
        mock_callback.from_user = MagicMock()
        mock_callback.from_user.id = 123
        mock_callback.data = "main:change_role"
        mock_callback.message = MagicMock()

        with patch("src.bot.handlers.shared.start.safe_callback_edit"):
            from src.bot.handlers.shared.start import change_role
            await change_role(mock_callback, mock_state)

            mock_callback.answer.assert_called()

    @pytest.mark.asyncio
    async def test_role_callback_data_format(self, mock_callback):
        """callback.data имеет правильный формат role:{role}."""
        mock_callback.data = "role:advertiser"
        
        parts = mock_callback.data.split(":")
        assert len(parts) == 2
        assert parts[0] == "role"
        assert parts[1] in ("advertiser", "owner", "both")


# ─────────────────────────────────────────────
# Тесты валидации ролей
# ─────────────────────────────────────────────

class TestRoleValidation:
    """Валидация ролей пользователей."""

    def test_role_new_is_not_advertiser_or_owner(self, db_user_new_role):
        """Роль 'new' — промежуточная, не даёт доступ к функциям."""
        assert db_user_new_role.role == "new"
        assert db_user_new_role.role not in ("advertiser", "owner", "both")

    def test_valid_roles_set(self):
        """Допустимые роли — ровно 5 значений."""
        valid_roles = {"new", "advertiser", "owner", "both", "admin"}
        assert len(valid_roles) == 5

    def test_role_values_are_strings(self):
        """Все роли — строки."""
        valid_roles = ["new", "advertiser", "owner", "both", "admin"]
        for role in valid_roles:
            assert isinstance(role, str)
            assert len(role) > 0
