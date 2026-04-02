"""Unit тесты клавиатур главного меню."""

import pytest
from aiogram.types import InlineKeyboardMarkup

from src.bot.keyboards.shared.main_menu import main_menu_kb, role_select_kb, tos_kb


class TestMainMenuKb:
    """Тесты главного меню (main_menu_kb)."""

    def test_returns_inline_markup(self):
        """Функция возвращает InlineKeyboardMarkup."""
        kb = main_menu_kb()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_cabinet_button(self):
        """Меню содержит кнопку кабинета."""
        kb = main_menu_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "main:cabinet" in callbacks

    def test_has_change_role_button(self):
        """Меню содержит кнопку смены роли."""
        kb = main_menu_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "main:change_role" in callbacks

    def test_has_help_and_feedback(self):
        """Меню содержит кнопки помощи и обратной связи."""
        kb = main_menu_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "main:help" in callbacks
        assert "main:feedback" in callbacks

    def test_at_least_two_rows(self):
        """В меню не менее двух рядов кнопок."""
        kb = main_menu_kb()
        assert len(kb.inline_keyboard) >= 2


class TestRoleSelectKb:
    """Тесты клавиатуры выбора роли (role_select_kb)."""

    def test_returns_inline_markup(self):
        """Функция возвращает InlineKeyboardMarkup."""
        kb = role_select_kb()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_advertiser_option(self):
        """Есть кнопка выбора роли рекламодателя."""
        kb = role_select_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "role:advertiser" in callbacks

    def test_has_owner_option(self):
        """Есть кнопка выбора роли владельца канала."""
        kb = role_select_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "role:owner" in callbacks

    def test_has_back_button(self):
        """Есть кнопка возврата в главное меню."""
        kb = role_select_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "main:main_menu" in callbacks

    def test_exactly_three_rows(self):
        """Клавиатура содержит ровно 3 ряда."""
        kb = role_select_kb()
        assert len(kb.inline_keyboard) == 3


class TestTosKb:
    """Тесты клавиатуры принятия условий (tos_kb)."""

    def test_returns_inline_markup(self):
        """Функция возвращает InlineKeyboardMarkup."""
        kb = tos_kb()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_accept_button(self):
        """Есть кнопка принятия условий."""
        kb = tos_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "terms:accept" in callbacks

    def test_has_decline_button(self):
        """Есть кнопка отклонения условий."""
        kb = tos_kb()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        callbacks = [btn.callback_data for btn in buttons]
        assert "terms:decline" in callbacks

    def test_exactly_two_rows(self):
        """Клавиатура содержит ровно 2 ряда."""
        kb = tos_kb()
        assert len(kb.inline_keyboard) == 2
