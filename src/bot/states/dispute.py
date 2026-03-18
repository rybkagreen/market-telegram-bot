"""Dispute states."""

from aiogram.fsm.state import State, StatesGroup


class DisputeStates(StatesGroup):
    """Состояния споров."""

    owner_explaining = State()
    advertiser_commenting = State()
    admin_reviewing = State()
