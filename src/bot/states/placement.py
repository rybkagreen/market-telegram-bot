"""Placement states."""

from aiogram.fsm.state import State, StatesGroup


class PlacementStates(StatesGroup):
    """Состояния wizard создания размещения."""

    selecting_category = State()
    selecting_channels = State()
    selecting_format = State()
    entering_text = State()
    arbitrating = State()
    waiting_response = State()
    upload_video = State()  # optional video upload step after text
