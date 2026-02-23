"""
Handlers для работы с шаблонами рекламных текстов.
"""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.data.templates import (
    CATEGORIES,
    TEMPLATES,
    get_template_by_id,
    get_templates_by_category,
)
from src.bot.keyboards.campaign import CampaignCB
from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.states.campaign import CampaignStates
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(MainMenuCB.filter(lambda cb: cb.action == "templates"))
async def handle_templates_menu(callback: CallbackQuery) -> None:
    """
    Показать меню категорий шаблонов.

    Args:
        callback: Callback query.
    """
    text = (
        "📋 <b>Библиотека шаблонов</b>\n\n"
        "Выберите категорию для просмотра шаблонов:\n\n"
    )

    builder = InlineKeyboardBuilder()
    for category in CATEGORIES:
        count = len(TEMPLATES.get(category, []))
        builder.button(
            text=f"{category} ({count})",
            callback_data=CampaignCB(action="template_category", value=category)
        )

    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(2, 2, 2, 2, 1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(CampaignCB.filter(lambda cb: cb.action == "template_category"))
async def handle_category_selected(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Показать шаблоны выбранной категории.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    category = callback_data.value
    templates = get_templates_by_category(category)

    if not templates:
        await callback.answer("❌ В этой категории нет шаблонов", show_alert=True)
        return

    text = f"📋 <b>Шаблоны: {category}</b>\n\n"
    text += "Выберите шаблон для просмотра:\n\n"

    builder = InlineKeyboardBuilder()
    for template in templates:
        builder.button(
            text=f"📄 {template['title']}",
            callback_data=CampaignCB(action="template_preview", value=template["id"])
        )

    builder.button(text="← Назад", callback_data=CampaignCB(action="template_back"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(2, 2)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(CampaignCB.filter(lambda cb: cb.action == "template_preview"))
async def handle_template_preview(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Показать превью шаблона.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    template_id = callback_data.value
    template = get_template_by_id(template_id)

    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return

    text = (
        f"📄 <b>{template['title']}</b>\n\n"
        f"{template['text']}\n\n"
        f"💡 <i>Плейсхолдеры вроде {{телефон}} нужно заменить на ваши данные.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Использовать",
        callback_data=CampaignCB(action="template_use", value=template_id)
    )
    builder.button(
        text="← Назад",
        callback_data=CampaignCB(action="template_back")
    )
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu")
    )
    builder.adjust(2, 1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(CampaignCB.filter(lambda cb: cb.action == "template_back"))
async def handle_template_back(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Вернуться к списку категорий.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    # Получаем предыдущую категорию из данных состояния
    # Для простоты просто возвращаемся в меню шаблонов
    text = (
        "📋 <b>Библиотека шаблонов</b>\n\n"
        "Выберите категорию:\n\n"
    )

    builder = InlineKeyboardBuilder()
    for category in CATEGORIES:
        count = len(TEMPLATES.get(category, []))
        builder.button(
            text=f"{category} ({count})",
            callback_data=CampaignCB(action="template_category", value=category)
        )

    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(2, 2, 2, 2, 1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(CampaignCB.filter(lambda cb: cb.action == "template_use"))
async def handle_use_template(
    callback: CallbackQuery,
    callback_data: CampaignCB,
    state: FSMContext,
) -> None:
    """
    Использовать шаблон для создания кампании.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    template_id = callback_data.value
    template = get_template_by_id(template_id)

    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return

    # Сохраняем текст шаблона в состоянии
    await state.update_data(
        text=template["text"],
        template_id=template_id,
        template_title=template["title"],
    )

    # Получаем текущее состояние
    current_state = await state.get_state()

    if current_state is None:
        # Начинаем wizard с шага выбора тематики
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(callback.from_user.id)

            if not user:
                await callback.answer("❌ Пользователь не найден", show_alert=True)
                return

        # Сначала запрашиваем название
        text = (
            f"✅ Шаблон «{template['title']}» выбран!\n\n"
            f"Теперь придумайте название для кампании (3-100 символов):"
        )

        await callback.message.edit_text(text)
        await state.set_state(CampaignStates.waiting_title)
        await state.update_data(step="title")
    else:
        # Продолжаем wizard — переходим к выбору тематики
        text = (
            f"✅ Шаблон «{template['title']}» выбран!\n\n"
            f"Теперь выберите тематику кампании:"
        )

        await callback.message.edit_text(text, reply_markup=get_topics_kb())
        await state.set_state(CampaignStates.waiting_topic)
        await state.update_data(step="topic")


# Импортируем клавиатуру здесь чтобы избежать circular imports
from src.bot.keyboards.campaign import get_topics_kb  # noqa: E402
