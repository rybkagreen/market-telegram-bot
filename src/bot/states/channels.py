"""FSM состояния для фильтров каталога каналов."""

from aiogram.fsm.state import State, StatesGroup


class ChannelFilterStates(StatesGroup):
    """Состояния для фильтров каталога."""

    browsing = State()  # Просмотр без фильтров
    filtering = State()  # Режим выбора фильтров
