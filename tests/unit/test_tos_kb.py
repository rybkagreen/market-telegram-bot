"""Unit тесты клавиатуры принятия условий (tos_kb)."""

from aiogram.types import InlineKeyboardMarkup

from src.bot.keyboards.shared.main_menu import tos_kb


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
