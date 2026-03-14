"""
Placement Entry Point — точка входа для placement флоу.
S-PLACEMENT-ENTRY: перехватывает main:create_campaign, показывает развилку, добавляет шаги категория → канал.

Порядок проверок:
1. main:create_campaign → развилка broadcast/placement
2. placement_entry:type:placement → выбор категории
3. placement_entry:cat:{key} → (subcategory если есть) → выбор канала
4. placement_entry:subcat:{key} → выбор канала
5. placement:select_channel → существующий placement флоу
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage

from src.bot.keyboards.advertiser.campaign_ai import CAMPAIGN_CATEGORIES
from src.bot.keyboards.advertiser.placement_entry import (
    kb_placement_categories,
    kb_type_fork,
)
from src.bot.keyboards.shared.main_menu import MainMenuCB
from src.bot.states.campaign_create import CampaignCreateState
from src.bot.states.placement_entry import PlacementEntryState
from src.bot.utils.safe_callback import safe_callback_edit

logger = logging.getLogger(__name__)

router = Router(name="placement_entry")


# ══════════════════════════════════════════════════════════════
# HANDLER 1: Перехват main:create_campaign — показываем развилку
# ══════════════════════════════════════════════════════════════


@router.callback_query(MainMenuCB.filter(F.action == "create_campaign"))
async def intercept_create_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Перехватывает main:create_campaign ДО AI wizard.
    Показывает развилку broadcast/placement.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.clear()
    await state.set_state(PlacementEntryState.selecting_type)

    text = (
        "🚀 <b>Создать кампанию</b>\n\n"
        "Выберите тип размещения:\n\n"
        "• <b>Placement</b> — размещение в конкретном канале\n"
        "• <b>Broadcast</b> — массовая рассылка по каналам"
    )

    await safe_callback_edit(callback, text=text, reply_markup=kb_type_fork())
    await callback.answer()


# ══════════════════════════════════════════════════════════════
# HANDLER 2: Broadcast — передаём управление AI wizard
# ══════════════════════════════════════════════════════════════


@router.callback_query(F.data == "placement_entry:type:broadcast")
async def select_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбран Broadcast — передаём управление AI wizard.
    Устанавливаем CampaignCreateState.selecting_style.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.clear()
    await state.set_state(CampaignCreateState.selecting_style)

    # Импортируем entry-point функцию из AI wizard
    from src.bot.handlers.advertiser.campaign_create_ai import start_campaign_create

    # Передаём управление AI wizard
    await start_campaign_create(callback, state)
    await callback.answer()


# ══════════════════════════════════════════════════════════════
# HANDLER 3: Placement — показываем выбор категории
# ══════════════════════════════════════════════════════════════


@router.callback_query(F.data == "placement_entry:type:placement")
async def select_placement(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбран Placement — показываем выбор категории.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(PlacementEntryState.selecting_category)

    text = (
        "📂 <b>Шаг 1/3: Категория</b>\n\n"
        "Выберите категорию вашей рекламы:\n\n"
        "Это поможет подобрать подходящие каналы."
    )

    await safe_callback_edit(callback, text=text, reply_markup=kb_placement_categories())
    await callback.answer()


# ══════════════════════════════════════════════════════════════
# HANDLER 4: Выбрана категория — переход к выбору канала
# ══════════════════════════════════════════════════════════════


@router.callback_query(F.data.startswith("placement_entry:cat:"))
async def category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Категория выбрана — сохраняем и переходим к выбору канала.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    category_key = callback.data.split(":")[2]
    category_name = CAMPAIGN_CATEGORIES.get(category_key, category_key)

    await state.update_data(category=category_key, category_name=category_name)

    # Нет подкатегорий — сразу к выбору канала
    await _go_to_channel_select(callback, state)
    await callback.answer()


# ══════════════════════════════════════════════════════════════
# HANDLER 5: Back to fork
# ══════════════════════════════════════════════════════════════


@router.callback_query(F.data == "placement_entry:back:fork")
async def back_to_fork(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Возврат к развилке broadcast/placement.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await state.set_state(PlacementEntryState.selecting_type)

    text = (
        "🚀 <b>Создать кампанию</b>\n\n"
        "Выберите тип размещения:"
    )

    await safe_callback_edit(callback, text=text, reply_markup=kb_type_fork())
    await callback.answer()


# ══════════════════════════════════════════════════════════════
# HELPER: Переход к выбору канала
# ══════════════════════════════════════════════════════════════


async def _go_to_channel_select(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Переход к выбору канала — эмулируем callback placement:select_channel.

    Это передаёт управление в существующий handle_select_channel из placement.py.
    """
    data = await state.get_data()
    category = data.get("category")
    category_name = data.get("category_name", category)

    logger.info(f"Placement entry: category={category}, name={category_name}")

    # Эмулируем callback для placement:select_channel
    # Это вызовет handle_select_channel из placement.py
    from src.bot.handlers.placement.placement import handle_select_channel

    # Создаём фейковый callback с нужными данными
    class FakeCallback:
        def __init__(self, original: CallbackQuery):
            self.message = original.message
            self.from_user = original.from_user
            self.data = "placement:select_channel"

        async def answer(self, *args, **kwargs):
            pass

    fake_callback = FakeCallback(callback)

    # Вызываем handle_select_channel
    await handle_select_channel(fake_callback)
