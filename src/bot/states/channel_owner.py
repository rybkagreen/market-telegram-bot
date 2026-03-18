"""Channel owner states."""

from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    """Состояния добавления канала."""

    entering_username = State()
    confirming = State()
