"""FSM состояния для размещения."""

from aiogram.fsm.state import State, StatesGroup


class PlacementStates(StatesGroup):
    """Состояния для создания заявки на размещение."""

    waiting_post_text = State()
    waiting_post_media = State()
    waiting_schedule_date = State()
    waiting_cancel_confirm = State()
