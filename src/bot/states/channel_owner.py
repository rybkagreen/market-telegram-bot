"""
FSM States для добавления канала владельцем.
"""

from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    """Состояния для добавления канала."""

    waiting_username = State()
    waiting_bot_admin_confirmation = State()
    waiting_price = State()
    waiting_topics = State()
    waiting_settings = State()
    waiting_confirm = State()


class EditChannelStates(StatesGroup):
    """Состояния для редактирования канала."""

    waiting_new_price = State()
    waiting_new_username = State()


class PayoutRequestStates(StatesGroup):
    """Состояния для запроса выплаты."""

    selecting_method = State()
    entering_address = State()
    confirming = State()


# Alias for backward compatibility
ChannelOwnerStates = AddChannelStates
