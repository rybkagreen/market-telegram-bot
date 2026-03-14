"""
FSM States для администратора.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния для административных действий."""

    entering_broadcast = State()  # ввод текста рассылки
    reviewing_dispute = State()  # просмотр диспута
    entering_resolution = State()  # ввод резолюции диспута
