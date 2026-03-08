"""
FSM состояния для создания кампании с AI.
"""

from aiogram.fsm.state import State, StatesGroup


class CampaignCreateState(StatesGroup):
    """Состояния для создания кампании с AI."""

    # Выбор стиля текста
    selecting_style = State()

    # Выбор категории (или ввод своей)
    selecting_category = State()
    entering_custom_category = State()

    # Ожидание описания продукта
    waiting_for_description = State()

    # Ввод названия кампании (топик)
    waiting_for_campaign_name = State()

    # Выбор варианта текста
    selecting_variant = State()

    # Редактирование текста
    editing_text = State()

    # Добавление URL
    waiting_for_url = State()

    # Добавление изображения
    waiting_for_image = State()

    # Настройки таргетинга
    selecting_audience = State()
    setting_budget = State()
    setting_schedule = State()
    entering_schedule_date = State()  # Ввод даты вручную

    # Финальное подтверждение
    confirming = State()
