"""FSM состояния для медиакита канала."""

from aiogram.fsm.state import State, StatesGroup


class MediakitStates(StatesGroup):
    """Состояния для редактирования медиакита."""

    waiting_logo = State()  # Ожидание загрузки логотипа
    waiting_description = State()  # Ожидание ввода описания
    waiting_color = State()  # Выбор цвета темы
