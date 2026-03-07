"""FSM состояния для хэндлеров владельца канала."""
from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    """Состояния мастера добавления канала."""

    waiting_username = State()  # ожидаем @username канала
    waiting_bot_admin_confirmation = State()  # НОВОЕ: подтверждение что бот добавлен админом
    waiting_price = State()  # ожидаем цену за пост
    waiting_topics = State()  # ожидаем выбор тематик
    waiting_settings = State()  # НОВОЕ: настройки размещения
    waiting_confirm = State()  # НОВОЕ: подтверждение добавления


class EditChannelStates(StatesGroup):
    """Состояния редактирования настроек канала."""

    waiting_new_price = State()  # ввод новой цены
    choosing_topics = State()  # выбор тематик
