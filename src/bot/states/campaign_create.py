"""
FSM состояния для создания кампании с AI.
"""

from aiogram.fsm.state import State, StatesGroup


class CampaignCreateState(StatesGroup):
    """Состояния для создания кампании с AI."""

    # Выбор тематики
    selecting_topic = State()

    # Ожидание описания продукта
    waiting_for_description = State()

    # Выбор варианта текста
    selecting_variant = State()

    # Редактирование текста
    editing_text = State()

    # Добавление URL
    waiting_for_url = State()

    # Добавление изображения
    waiting_for_image = State()

    # Финальное подтверждение
    confirming = State()
