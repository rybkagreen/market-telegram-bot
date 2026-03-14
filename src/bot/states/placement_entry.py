"""FSM состояния для точки входа placement флоу."""

from aiogram.fsm.state import State, StatesGroup


class PlacementEntryState(StatesGroup):
    """Состояния для выбора типа кампании и категории."""

    selecting_type = State()  # развилка broadcast/placement
    selecting_category = State()  # выбор категории для placement
    selecting_subcategory = State()  # выбор подкатегории (если есть)
