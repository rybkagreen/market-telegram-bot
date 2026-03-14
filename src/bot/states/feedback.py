"""
FSM States для обратной связи.
"""

from aiogram.fsm.state import State, StatesGroup


class FeedbackStates(StatesGroup):
    """Состояния для отправки обратной связи."""

    choosing_type = State()
    waiting_text = State()
    waiting_confirm = State()
