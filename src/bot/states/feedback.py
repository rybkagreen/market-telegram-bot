"""Feedback states."""

from aiogram.fsm.state import State, StatesGroup


class FeedbackStates(StatesGroup):
    """Состояния отправки обратной связи."""

    entering_text = State()
