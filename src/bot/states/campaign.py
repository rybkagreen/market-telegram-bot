"""
FSM состояния для wizard'а создания кампании.
"""

from aiogram.fsm.state import State, StatesGroup


class CampaignStates(StatesGroup):
    """
    Состояния для создания рекламной кампании.

    States:
        waiting_title: Ожидание названия кампании
        waiting_topic: Ожидание выбора тематики
        waiting_header: Ожидание заголовка
        waiting_text: Ожидание текста (выбор: вручную или ИИ)
        waiting_ai_description: Ожидание описания для ИИ-генерации
        waiting_image: Ожидание изображения (опционально)
        waiting_member_count: Ожидание выбора размера аудитории
        waiting_schedule: Ожидание выбора расписания
        waiting_confirm: Ожидание подтверждения запуска
    """

    waiting_title = State()
    waiting_topic = State()
    waiting_header = State()
    waiting_text = State()
    waiting_ai_description = State()
    waiting_image = State()
    waiting_member_count = State()
    waiting_schedule = State()
    waiting_confirm = State()
