"""Admin feedback response states."""

from aiogram.fsm.state import State, StatesGroup


class AdminFeedbackStates(StatesGroup):
    """States for admin feedback response."""

    waiting_for_response = State()  # Ожидание текста ответа
