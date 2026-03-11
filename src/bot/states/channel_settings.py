"""FSM состояния для настроек канала."""

from aiogram.fsm.state import State, StatesGroup


class ChannelSettingsStates(StatesGroup):
    """Состояния для редактирования настроек канала."""

    waiting_price_per_post = State()
    waiting_start_time = State()
    waiting_end_time = State()
    waiting_break_start = State()
    waiting_break_end = State()
    waiting_daily_discount = State()
    waiting_weekly_discount = State()
    waiting_sub_min_days = State()
    waiting_sub_max_days = State()
