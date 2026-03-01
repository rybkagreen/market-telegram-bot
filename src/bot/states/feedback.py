"""
FSM состояния для обратной связи и bug report.
"""
from aiogram.fsm.state import State, StatesGroup


class FeedbackStates(StatesGroup):
    """Состояния для отправки обратной связи."""

    choosing_type = State()    # выбор типа: отзыв или баг
    waiting_text = State()     # ввод текста
    waiting_confirm = State()  # подтверждение перед отправкой
