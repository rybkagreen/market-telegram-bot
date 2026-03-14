"""
FSM States для обратной связи.
"""

from aiogram.fsm.state import State, StatesGroup


class FeedbackStates(StatesGroup):
    """Состояния для отправки обратной связи."""

    entering_text = State()  # ввод текста сообщения
