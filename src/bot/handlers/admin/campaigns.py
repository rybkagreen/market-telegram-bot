"""
Admin Campaigns Handlers — тестирование и бесплатные кампании.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.filters.admin import AdminFilter
from src.bot.keyboards.admin.admin import (
    AdminCB,
    get_admin_confirm_kb,
    get_admin_main_kb,
    get_back_kb,
)
from src.bot.keyboards.advertiser.campaign import (
    CampaignCB,
    get_member_count_kb,
    get_schedule_kb,
)
from src.bot.states.admin import AdminFreeCampaignStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.models.campaign import CampaignStatus
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.utils.content_filter.filter import check as content_filter_check

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# ==================== ТЕСТ КАМПАНИИ ====================


@router.callback_query(AdminCB.filter(F.action == "test_campaign"))
async def show_test_campaign_menu(callback: CallbackQuery) -> None:
    """Тестирование кампании — объединённый раздел."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🤖 ИИ-генерация текста", callback_data=AdminCB(action="ai_generate"))
    builder.button(text="📣 Запустить без оплаты", callback_data=AdminCB(action="free_campaign"))
    builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
    builder.adjust(1)

    await safe_callback_edit(
        callback, "🧪 <b>Тест кампании</b>\n\nВыберите действие:", reply_markup=builder.as_markup()
    )
    await callback.answer()


# ==================== БЕСПЛАТНАЯ КАМПАНИЯ (ДЛЯ АДМИНА) ====================


@router.callback_query(AdminCB.filter(F.action == "free_campaign"))
async def handle_free_campaign_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать создание бесплатной кампании для админа."""
    await state.clear()
    await state.update_data(is_free=True, admin_id=callback.from_user.id)
    await state.set_state(AdminFreeCampaignStates.waiting_title)

    await safe_callback_edit(
        callback,
        "📣 <b>Бесплатная кампания администратора</b>\n\nВведите название кампании:",
        reply_markup=get_back_kb(),
    )
    await callback.answer()


@router.message(AdminFreeCampaignStates.waiting_title)
async def handle_free_campaign_title(message: Message, state: FSMContext) -> None:
    """Обработать название кампании."""
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return
    title = message.text.strip()

    if len(title) < 3 or len(title) > 100:
        await message.answer("❌ Название должно быть от 3 до 100 символов.")
        return

    await state.update_data(title=title)
    await state.set_state(AdminFreeCampaignStates.waiting_text)
    await message.answer("Введите текст рекламного сообщения:")


@router.message(AdminFreeCampaignStates.waiting_text)
async def handle_free_campaign_text(message: Message, state: FSMContext) -> None:
    """Обработать текст кампании."""
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return
    text = message.text.strip()

    # Content filter проверяет даже для админа
    filter_result = await content_filter_check(text)
    if not filter_result.passed:
        await message.answer(
            f"⚠️ Текст не прошёл проверку: {', '.join(filter_result.categories)}\n"
            f"Фрагменты: {', '.join(filter_result.flagged_fragments)}\n\n"
            "Введите другой текст:"
        )
        return

    await state.update_data(text=text)
    await state.set_state(AdminFreeCampaignStates.waiting_topic)

    builder = InlineKeyboardBuilder()
    for topic in ["бизнес", "маркетинг", "it", "финансы", "крипто", "образование"]:
        builder.button(
            text=topic.capitalize(), callback_data=CampaignCB(action="topic", value=topic)
        )
    builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
    builder.adjust(2)

    await message.answer("Выберите тематику кампании:", reply_markup=builder.as_markup())


@router.callback_query(
    AdminFreeCampaignStates.waiting_topic, CampaignCB.filter(F.action == "topic")
)
async def handle_free_campaign_topic(
    callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext
) -> None:
    """Выбрать тематику кампании."""
    topic = callback_data.value
    await state.update_data(topic=topic)
    await state.set_state(AdminFreeCampaignStates.waiting_member_count)

    await safe_callback_edit(
        callback,
        f"✅ Тематика: {topic}\n\nВыберите минимальное количество подписчиков:",
        reply_markup=get_member_count_kb(),
    )
    await callback.answer()


@router.callback_query(
    AdminFreeCampaignStates.waiting_member_count, CampaignCB.filter(F.action == "member_count")
)
async def handle_free_campaign_members(
    callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext
) -> None:
    """Выбрать минимальное количество подписчиков."""
    min_members = int(callback_data.value)
    await state.update_data(min_members=min_members)
    await state.set_state(AdminFreeCampaignStates.waiting_schedule)

    await safe_callback_edit(
        callback,
        f"✅ Минимум подписчиков: {min_members}\n\nВыберите расписание:",
        reply_markup=get_schedule_kb(),
    )
    await callback.answer()


@router.callback_query(
    AdminFreeCampaignStates.waiting_schedule, CampaignCB.filter(F.action == "schedule")
)
async def handle_free_campaign_schedule(
    callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext
) -> None:
    """Выбрать расписание."""
    schedule = callback_data.value
    await state.update_data(schedule=schedule)
    await state.set_state(AdminFreeCampaignStates.confirming)

    data = await state.get_data()
    preview = (
        f"📣 <b>Предпросмотр кампании</b>\n\n"
        f"Название: {data.get('title')}\n"
        f"Тематика: {data.get('topic')}\n"
        f"Мин. подписчиков: {data.get('min_members')}\n"
        f"Расписание: {data.get('schedule')}\n\n"
        f"Текст:\n{(data.get('text') or '')[:500]}..."
    )

    await safe_callback_edit(callback, preview, reply_markup=get_admin_confirm_kb("free_campaign"))
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "free_campaign_confirm"))
async def handle_free_campaign_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтвердить и создать бесплатную кампанию."""
    data = await state.get_data()
    await state.clear()

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        campaign_repo = CampaignRepository(session)

        # Находим админа
        admin = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not admin:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Создаём кампанию
        campaign = await campaign_repo.create(
            {
                "user_id": admin.id,
                "title": data.get("title"),
                "text": data.get("text"),
                "topic": data.get("topic"),
                "status": CampaignStatus.DRAFT.value,
                "filters_json": {"min_members": data.get("min_members")},
                "cost": 0,  # Бесплатно для админа
            }
        )
        await session.commit()

    await safe_callback_edit(
        callback,
        f"✅ <b>Кампания создана!</b>\n\nID: {campaign.id}\nЗапускаю...",
        reply_markup=get_admin_main_kb(),
    )
    await callback.answer()
