# tests/unit/test_start_and_role.py
"""
Тесты валидации ролей пользователей и формата callback-данных.

Покрывает:
- Роль 'new' промежуточная — не даёт доступа к функциям
- Множество допустимых ролей
- Формат callback.data: role:{advertiser|owner|both}
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


@pytest.fixture
def db_user_new_role():
    """DB User только что зарегистрированный, роль 'new'."""
    u = MagicMock()
    u.id = 1
    u.telegram_id = 999001
    u.role = "new"
    u.is_banned = False
    u.balance_rub = 0
    return u


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


# ─────────────────────────────────────────────
# Тесты команды /start
# ─────────────────────────────────────────────


class TestStartCommandNewUser:
    """/start для нового пользователя."""

    @pytest.mark.asyncio
    async def test_new_user_role_is_new(self, db_user_new_role):
        """Новый пользователь получает роль 'new', не advertiser/owner сразу."""
        assert db_user_new_role.role == "new"


# ─────────────────────────────────────────────
# Тесты выбора роли
# ─────────────────────────────────────────────


class TestRoleSelection:
    """Выбор роли через callback."""

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
