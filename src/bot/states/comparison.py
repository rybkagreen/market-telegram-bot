"""FSM состояния для сравнения каналов."""

from aiogram.fsm.state import State, StatesGroup


class ChannelComparisonStates(StatesGroup):
    """Состояния для сравнения каналов."""

    selecting = State()  # Выбор каналов
    comparing = State()  # Просмотр сравнения
