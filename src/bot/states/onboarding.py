"""
FSM состояния для онбординга пользователей.
"""

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Состояния онбординга нового пользователя."""

    # Пользователь выбрал роль, но ещё не завершил онбординг
    role_selected = State()  # role: "advertiser" | "owner"
