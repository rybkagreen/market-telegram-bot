"""FSM состояния для хэндлеров владельца канала."""
from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    """Состояния мастера добавления канала."""

    waiting_username = State()  # ожидаем @username канала
    waiting_verification = State()  # ожидаем нажатия «Проверить»
    waiting_price = State()  # ожидаем цену за пост
    waiting_topics = State()  # ожидаем выбор тематик


class EditChannelStates(StatesGroup):
    """Состояния редактирования настроек канала."""

    waiting_new_price = State()  # ввод новой цены
    choosing_topics = State()  # выбор тематик
