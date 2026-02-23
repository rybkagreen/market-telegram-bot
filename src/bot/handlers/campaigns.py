"""
FSM wizard для создания рекламной кампании.
"""

import logging
import re
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.campaign import (
    CampaignCB,
    get_campaign_confirm_kb,
    get_campaign_step_kb,
    get_member_count_kb,
    get_schedule_kb,
    get_text_type_kb,
    get_topics_kb,
)
from src.bot.keyboards.main_menu import MainMenuCB, get_main_menu
from src.bot.states.campaign import CampaignStates
from src.core.services.ai_service import ai_service
from src.db.models.campaign import CampaignStatus
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.mailing_tasks import send_campaign
from src.utils.content_filter.filter import check as content_filter_check

logger = logging.getLogger(__name__)

router = Router()


# ==================== СТАРТ WIZARD'А ====================


@router.callback_query(MainMenuCB.filter(F.action == "create_campaign"))
async def start_campaign_wizard(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать wizard создания кампании.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.clear()
    await state.update_data(step="title")

    text = (
        "📝 <b>Создание кампании</b>\n\n"
        "Придумайте название для вашей кампании.\n"
        "Это нужно для вашего удобства — название видят только вы.\n\n"
        "📏 Длина: от 3 до 100 символов"
    )

    await callback.message.edit_text(text, reply_markup=get_campaign_step_kb(back=False))
    await state.set_state(CampaignStates.waiting_title)


# ==================== ШАГ 1: НАЗВАНИЕ ====================


@router.message(CampaignStates.waiting_title)
async def handle_title_input(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод названия кампании.

    Args:
        message: Сообщение с названием.
        state: FSM контекст.
    """
    title = message.text.strip()

    # Валидация длины
    if len(title) < 3:
        await message.answer(
            "❌ Название слишком короткое (минимум 3 символа).\n\n"
            "Введите название кампании:"
        )
        return

    if len(title) > 100:
        await message.answer(
            "❌ Название слишком длинное (максимум 100 символов).\n\n"
            "Введите название кампании:"
        )
        return

    # Сохраняем название
    await state.update_data(title=title)

    # Переход к шагу 2: выбор типа текста
    text = (
        "✍️ <b>Текст кампании</b>\n\n"
        "Как вы хотите создать текст для рассылки?"
    )

    await message.answer(text, reply_markup=get_text_type_kb())
    await state.update_data(step="text_type")


# ==================== ШАГ 2: ВЫБОР ТИПА ТЕКСТА ====================


@router.callback_query(CampaignStates.waiting_text, CampaignCB.filter(F.action == "back"))
async def back_from_text_type(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к шагу названия.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(None)
    await state.update_data(step="title")

    text = (
        "📝 <b>Название кампании</b>\n\n"
        "Введите название кампании (3-100 символов):"
    )

    await callback.message.edit_text(text, reply_markup=get_campaign_step_kb(back=False))
    await state.set_state(CampaignStates.waiting_title)


@router.callback_query(CampaignStates.waiting_text, CampaignCB.filter(F.action == "manual_text"))
async def select_manual_text(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбран ручной ввод текста.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.update_data(text_type="manual")

    text = (
        "✏️ <b>Введите текст кампании</b>\n\n"
        "Текст должен быть информативным и привлекательным.\n"
        "Можно использовать эмодзи для привлечения внимания.\n\n"
        "📏 Рекомендуемая длина: 150-500 символов"
    )

    await callback.message.edit_text(text, reply_markup=get_campaign_step_kb())
    await state.update_data(step="manual_text")


@router.callback_query(CampaignStates.waiting_text, CampaignCB.filter(F.action == "ai_text"))
async def select_ai_text(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбрана ИИ-генерация текста.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.update_data(text_type="ai")

    text = (
        "🤖 <b>Генерация текста через ИИ</b>\n\n"
        "Опишите ваш продукт или услугу, и ИИ создаст текст за вас.\n"
        "Стоимость генерации: <b>10₽</b>\n\n"
        "Пример описания:\n"
        "«Онлайн-курс по Python для начинающих. Длительность 3 месяца, практика, дипломный проект.»"
    )

    await callback.message.edit_text(text, reply_markup=get_campaign_step_kb())
    await state.set_state(CampaignStates.waiting_ai_description)
    await state.update_data(step="ai_description")


# ==================== ШАГ 2a: AI ОПИСАНИЕ ====================


@router.message(CampaignStates.waiting_ai_description)
async def handle_ai_description(message: Message, state: FSMContext) -> None:
    """
    Обработать описание для ИИ-генерации.

    Args:
        message: Сообщение с описанием.
        state: FSM контекст.
    """
    description = message.text.strip()

    if len(description) < 10:
        await message.answer(
            "❌ Описание слишком короткое (минимум 10 символов).\n\n"
            "Опишите ваш продукт или услугу подробнее:"
        )
        return

    # Сохраняем описание
    await state.update_data(ai_description=description)

    # Генерируем варианты
    status_message = await message.answer("🤖 Генерирую варианты текстов...")

    try:
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(message.from_user.id)

            if not user:
                await status_message.edit_text("❌ Пользователь не найден")
                return

            # Проверяем баланс
            cost = 30.0  # 3 варианта по 10₽
            if user.balance < cost:
                await status_message.edit_text(
                    f"❌ Недостаточно средств. Нужно {cost}₽, у вас {user.balance}₽.\n\n"
                    "Пополните баланс и попробуйте снова."
                )
                await state.set_state(None)
                await state.update_data(step="")
                return

        # Генерируем A/B варианты
        variants = await ai_service.generate_ab_variants(
            user_id=message.from_user.id,
            description=description,
            count=3,
        )

        await status_message.delete()

        # Показываем варианты
        text = (
            "🤖 <b>Варианты текста от ИИ</b>\n\n"
            "Выберите подходящий вариант:\n\n"
        )

        builder = InlineKeyboardBuilder()
        for i, variant in enumerate(variants, 1):
            text += f"<b>Вариант {i}:</b>\n{variant}\n\n"
            builder.button(
                text=f"✅ Вариант {i}",
                callback_data=CampaignCB(action="ai_variant", value=str(i))
            )

        builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
        builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
        builder.adjust(2, 2, 2)

        await message.answer(text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"AI generation error: {e}")
        await status_message.edit_text(
            f"❌ Ошибка генерации: {e}\n\n"
            "Попробуйте снова или введите текст вручную."
        )
        await state.set_state(CampaignStates.waiting_ai_description)


@router.callback_query(CampaignCB.filter(F.action == "ai_variant"))
async def select_ai_variant(callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext) -> None:
    """
    Выбрать вариант ИИ-текста.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    variant_index = int(callback_data.value) - 1

    data = await state.get_data()
    variants_text = data.get("ai_variants", [])

    # Получаем текст выбранного варианта (из данных состояния)
    # Для простоты regenerируем описание
    description = data.get("ai_description", "")

    # Генерируем заново для получения текста (в production лучше кэшировать)
    variants = await ai_service.generate_ab_variants(
        user_id=callback.from_user.id,
        description=description,
        count=3,
    )

    if variant_index < 0 or variant_index >= len(variants):
        await callback.answer("❌ Неверный вариант", show_alert=True)
        return

    selected_text = variants[variant_index]
    await state.update_data(text=selected_text)

    # Переход к выбору тематики
    await show_topic_selection(callback, state)


# ==================== РУЧНОЙ ВВОД ТЕКСТА ====================


@router.message(F.text, CampaignStates.waiting_text)
async def handle_manual_text_input(message: Message, state: FSMContext) -> None:
    """
    Обработать ручной ввод текста.

    Args:
        message: Сообщение с текстом.
        state: FSM контекст.
    """
    # Проверяем, что мы в состоянии ручного ввода
    data = await state.get_data()
    if data.get("step") != "manual_text":
        return

    text = message.text.strip()

    if len(text) < 20:
        await message.answer(
            "❌ Текст слишком короткий (минимум 20 символов).\n\n"
            "Введите текст кампании:"
        )
        return

    # Сохраняем текст
    await state.update_data(text=text)

    # Проверяем контент-фильтром
    filter_result = content_filter_check(text)

    if not filter_result.passed:
        categories = ", ".join(filter_result.categories)
        await message.answer(
            f"❌ Текст содержит запрещенный контент!\n\n"
            f"Категории: {categories}\n\n"
            "Пожалуйста, измените текст и попробуйте снова."
        )
        # Возвращаем к вводу текста
        return

    # Переход к выбору тематики
    await show_topic_selection(message, state)


async def show_topic_selection(target: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Показать выбор тематики.

    Args:
        target: Сообщение или callback query.
        state: FSM контекст.
    """
    await state.set_state(None)

    text = (
        "📌 <b>Тематика кампании</b>\n\n"
        "Выберите тематику, которая лучше всего подходит для вашей рекламы.\n"
        "Это поможет подобрать релевантные чаты для рассылки."
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=get_topics_kb())
    else:
        await target.answer(text, reply_markup=get_topics_kb())

    await state.set_state(CampaignStates.waiting_topic)
    await state.update_data(step="topic")


# ==================== ШАГ 3: ВЫБОР ТЕМАТИКИ ====================


@router.callback_query(CampaignStates.waiting_topic, CampaignCB.filter(F.action == "back"))
async def back_from_topic(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к выбору типа текста.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    data = await state.get_data()
    text_type = data.get("text_type", "manual")

    if text_type == "ai":
        await state.set_state(CampaignStates.waiting_ai_description)
        text = (
            "🤖 <b>Описание для ИИ</b>\n\n"
            "Опишите ваш продукт или услугу:"
        )
    else:
        await state.set_state(CampaignStates.waiting_text)
        text = (
            "✏️ <b>Текст кампании</b>\n\n"
            "Введите текст кампании:"
        )

    await callback.message.edit_text(text, reply_markup=get_campaign_step_kb())
    await state.update_data(step="text_type" if text_type == "ai" else "manual_text")


@router.callback_query(CampaignStates.waiting_topic, CampaignCB.filter(F.action == "topic"))
async def select_topic(callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext) -> None:
    """
    Выбрать тематику кампании.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    topic = callback_data.value
    await state.update_data(topic=topic)

    # Переход к выбору размера аудитории
    text = (
        f"👥 <b>Размер аудитории</b>\n\n"
        f"Выберите размер чатов для рассылки.\n"
        f"Тематика: <b>{topic}</b>"
    )

    await callback.message.edit_text(text, reply_markup=get_member_count_kb())
    await state.set_state(CampaignStates.waiting_member_count)
    await state.update_data(step="member_count")


# ==================== ШАГ 4: ВЫБОР РАЗМЕРА АУДИТОРИИ ====================


@router.callback_query(CampaignStates.waiting_member_count, CampaignCB.filter(F.action == "back"))
async def back_from_member_count(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к выбору тематики.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(CampaignStates.waiting_topic)

    text = (
        "📌 <b>Тематика кампании</b>\n\n"
        "Выберите тематику:"
    )

    await callback.message.edit_text(text, reply_markup=get_topics_kb())
    await state.update_data(step="topic")


@router.callback_query(CampaignStates.waiting_member_count, CampaignCB.filter(F.action == "members"))
async def select_member_count(callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext) -> None:
    """
    Выбрать размер аудитории.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    value = callback_data.value

    # Парсим диапазон
    if value == "any":
        min_members = 0
        max_members = 1000000
    else:
        parts = value.split("_")
        min_members = int(parts[0])
        max_members = int(parts[1])

    await state.update_data(
        min_members=min_members,
        max_members=max_members,
        member_count_label=value,
    )

    # Переход к выбору расписания
    text = (
        "⏰ <b>Расписание запуска</b>\n\n"
        "Когда запустить кампанию?"
    )

    await callback.message.edit_text(text, reply_markup=get_schedule_kb())
    await state.set_state(CampaignStates.waiting_schedule)
    await state.update_data(step="schedule")


# ==================== ШАГ 5: ВЫБОР РАСПИСАНИЯ ====================


@router.callback_query(CampaignStates.waiting_schedule, CampaignCB.filter(F.action == "back"))
async def back_from_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к выбору размера аудитории.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(CampaignStates.waiting_member_count)

    text = (
        "👥 <b>Размер аудитории</b>\n\n"
        "Выберите размер чатов:"
    )

    await callback.message.edit_text(text, reply_markup=get_member_count_kb())
    await state.update_data(step="member_count")


@router.callback_query(CampaignStates.waiting_schedule, CampaignCB.filter(F.action == "schedule_now"))
async def select_schedule_now(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запустить кампанию сейчас.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.update_data(schedule="now", scheduled_at=None)
    await show_confirmation(callback, state)


@router.callback_query(CampaignStates.waiting_schedule, CampaignCB.filter(F.action == "schedule_later"))
async def select_schedule_later(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запланировать кампанию на потом.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await callback.message.edit_text(
        "⏰ <b>Запланировать запуск</b>\n\n"
        "Введите дату и время в формате:\n"
        "<b>ДД.ММ.ГГГГ ЧЧ:ММ</b>\n\n"
        "Пример: 25.12.2024 15:30\n"
        "Минимум через 1 час от текущего времени."
    )
    await state.set_state(CampaignStates.waiting_schedule)
    await state.update_data(step="schedule_datetime")


@router.message(CampaignStates.waiting_schedule)
async def handle_schedule_datetime(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод даты и времени запуска.

    Args:
        message: Сообщение с датой.
        state: FSM контекст.
    """
    data = await state.get_data()
    if data.get("step") != "schedule_datetime":
        return

    datetime_str = message.text.strip()

    # Парсим дату
    pattern = r"^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}$"
    if not re.match(pattern, datetime_str):
        await message.answer(
            "❌ Неверный формат даты.\n\n"
            "Используйте формат: <b>ДД.ММ.ГГГГ ЧЧ:ММ</b>\n"
            "Пример: 25.12.2024 15:30"
        )
        return

    try:
        scheduled_at = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(
            "❌ Неверная дата или время.\n\n"
            "Проверьте правильность ввода:"
        )
        return

    # Проверяем, что дата не в прошлом
    now = datetime.now()
    if scheduled_at < now:
        await message.answer(
            "❌ Дата не может быть в прошлом.\n\n"
            "Введите будущую дату и время:"
        )
        return

    # Проверяем, что минимум через 1 час
    min_time = now.replace(minute=0, second=0, microsecond=0)
    if min_time.hour >= now.hour:
        min_time = min_time.replace(hour=min_time.hour + 1)
    else:
        min_time = min_time.replace(day=min_time.day + 1, hour=0)

    if scheduled_at < min_time:
        await message.answer(
            "❌ Кампания должна быть запланирована минимум за 1 час.\n\n"
            "Введите другую дату:"
        )
        return

    await state.update_data(scheduled_at=scheduled_at.isoformat(), schedule="later")
    await show_confirmation(message, state)


# ==================== ШАГ 6: ПОДТВЕРЖДЕНИЕ ====================


async def show_confirmation(target: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Показать карточку подтверждения кампании.

    Args:
        target: Сообщение или callback query.
        state: FSM контекст.
    """
    await state.set_state(CampaignStates.waiting_confirm)
    await state.update_data(step="confirm")

    data = await state.get_data()

    # Формируем карточку
    text = (
        "✅ <b>Подтверждение кампании</b>\n\n"
        f"📋 <b>Название:</b> {data.get('title', '—')}\n"
        f"📝 <b>Текст:</b>\n{data.get('text', '—')[:300]}{'...' if len(data.get('text', '')) > 300 else ''}\n\n"
        f"📌 <b>Тематика:</b> {data.get('topic', '—')}\n"
        f"👥 <b>Аудитория:</b> {data.get('member_count_label', '—')}\n"
    )

    scheduled_at = data.get("scheduled_at")
    if scheduled_at:
        schedule_str = datetime.fromisoformat(scheduled_at).strftime("%d.%m.%Y %H:%M")
        text += f"⏰ <b>Запуск:</b> {schedule_str}\n"
    else:
        text += "⏰ <b>Запуск:</b> Немедленно\n"

    text += "\nВыберите действие:"

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=get_campaign_confirm_kb())
    else:
        await target.answer(text, reply_markup=get_campaign_confirm_kb())


@router.callback_query(CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "back"))
async def back_from_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к выбору расписания.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(CampaignStates.waiting_schedule)

    text = (
        "⏰ <b>Расписание запуска</b>\n\n"
        "Когда запустить кампанию?"
    )

    await callback.message.edit_text(text, reply_markup=get_schedule_kb())
    await state.update_data(step="schedule")


@router.callback_query(CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "confirm_edit"))
async def confirm_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Редактировать кампанию (вернуться к тексту).

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.set_state(CampaignStates.waiting_text)

    text = (
        "✏️ <b>Редактирование текста</b>\n\n"
        "Введите новый текст кампании:"
    )

    await callback.message.edit_text(text, reply_markup=get_campaign_step_kb())
    await state.update_data(step="manual_text")


@router.callback_query(CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "confirm_draft"))
async def confirm_draft(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Сохранить как черновик.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        data = await state.get_data()

        campaign_repo = CampaignRepository(session)
        await campaign_repo.create({
            "user_id": user.id,
            "title": data.get("title", "Без названия"),
            "text": data.get("text", ""),
            "status": CampaignStatus.DRAFT,
            "filters_json": {
                "topics": [data.get("topic")],
                "min_members": data.get("min_members", 0),
                "max_members": data.get("max_members", 1000000),
            },
        })

    await state.clear()

    text = (
        "💾 <b>Черновик сохранён!</b>\n\n"
        "Кампания сохранена в черновиках.\n"
        "Вы можете запустить её позже из личного кабинета."
    )

    await callback.message.edit_text(text, reply_markup=get_main_menu(user.balance))


@router.callback_query(CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "confirm_launch"))
async def confirm_launch(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запустить кампанию.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем возможность запуска кампаний
        if not user.can_send_campaigns():
            await callback.answer(
                "❌ Ваш тариф не позволяет запускать кампании.\n"
                "Перейдите в кабинет для смены тарифа.",
                show_alert=True,
            )
            return

        data = await state.get_data()

        # Проверяем лимит кампаний
        campaign_count = await campaign_repo.get_user_campaigns_count(user.id)
        if campaign_count >= user.get_campaign_limit():
            await callback.answer(
                f"❌ Превышен лимит кампаний для вашего тарифа: {user.get_campaign_limit()}\n"
                "Перейдите в кабинет для смены тарифа.",
                show_alert=True,
            )
            return

        campaign_repo = CampaignRepository(session)

        # Парсим scheduled_at
        scheduled_at_str = data.get("scheduled_at")
        scheduled_at = None
        if scheduled_at_str:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)

        # Создаем кампанию
        campaign = await campaign_repo.create({
            "user_id": user.id,
            "title": data.get("title", "Без названия"),
            "text": data.get("text", ""),
            "ai_description": data.get("ai_description"),
            "status": CampaignStatus.QUEUED if scheduled_at else CampaignStatus.RUNNING,
            "filters_json": {
                "topics": [data.get("topic")],
                "min_members": data.get("min_members", 0),
                "max_members": data.get("max_members", 1000000),
            },
            "scheduled_at": scheduled_at,
        })

    await state.clear()

    if scheduled_at:
        text = (
            f"✅ <b>Кампания запланирована!</b>\n\n"
            f"📋 {campaign.title}\n"
            f"⏰ Запуск: {scheduled_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Вы получите уведомление о запуске."
        )
    else:
        text = (
            f"🚀 <b>Кампания запущена!</b>\n\n"
            f"📋 {campaign.title}\n\n"
            f"Мы отправим уведомление о завершении."
        )

        # Запускаем рассылку через Celery
        send_campaign.delay(campaign.id)

    await callback.message.edit_text(text, reply_markup=get_main_menu(user.balance))


# ==================== ОТМЕНА ====================


@router.callback_query(CampaignCB.filter(F.action == "cancel"))
async def cancel_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменить создание кампании.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await state.clear()

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

    text = "✖ Создание кампании отменено."

    if user:
        await callback.message.edit_text(text, reply_markup=get_main_menu(user.balance))
    else:
        await callback.message.edit_text(text)
        await callback.answer("❌ Пользователь не найден. Нажмите /start")
