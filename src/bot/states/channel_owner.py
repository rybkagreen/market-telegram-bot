"""
FSM States для добавления канала владельцем.
"""

from aiogram.fsm.state import State, StatesGroup


class ChannelOwnerStates(StatesGroup):
    """Состояния для добавления/редактирования канала."""

    entering_username = State()  # ввод username канала
    confirming_add = State()  # подтверждение добавления канала
