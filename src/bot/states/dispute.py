"""
FSM States для диспутов.
"""

from aiogram.fsm.state import State, StatesGroup


class DisputeStates(StatesGroup):
    """Состояния для диспутов."""

    owner_explaining = State()  # владелец объясняет ситуацию
    advertiser_commenting = State()  # рекламодатель комментирует
    admin_reviewing = State()  # администратор рассматривает
