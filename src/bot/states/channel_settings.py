"""Channel settings states."""

from aiogram.fsm.state import State, StatesGroup


class ChannelSettingsStates(StatesGroup):
    """Состояния настройки канала."""

    editing_price = State()
    editing_schedule = State()
    confirming = State()
