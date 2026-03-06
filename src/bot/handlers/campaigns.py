"""
FSM wizard для создания рекламной кампании (обновлённая версия).

Структура кампании:
1. Тема (тематика)
2. Заголовок
3. Рекламный текст (вручную или через ИИ)
4. Изображение (опционально)
5. Размер аудитории
6. Расписание
7. Подтверждение
"""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import (  # type: ignore[attr-defined]
    InlineKeyboardBuilder,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from src.bot.keyboards.cabinet import CabinetCB, get_notifications_prompt_kb
from src.bot.keyboards.campaign import (
    CampaignCB,
    get_campaign_confirm_kb,
    get_campaign_step_kb,
    get_image_upload_kb,
    get_member_count_kb,
    get_schedule_kb,
    get_text_type_kb,
    get_topics_kb,
)
from src.bot.keyboards.main_menu import MainMenuCB, get_main_menu
from src.bot.states.campaign import CampaignStates
from src.bot.utils.safe_callback import safe_callback_edit
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
    """
    await state.clear()

    text = (
        "📝 <b>Создание кампании</b>\n\n"
        "Шаг 1 из 7: Выберите тематику вашей кампании.\n\n"
        "Тематика поможет нам подобрать подходящие чаты для рассылки."
    )

    await safe_callback_edit(callback, text, reply_markup=get_topics_kb())
    await state.set_state(CampaignStates.waiting_topic)
    await state.update_data(step="topic")


# ==================== ШАГ 1: ТЕМАТИКА ====================


@router.callback_query(CampaignStates.waiting_topic, CampaignCB.filter(F.action == "topic"))
async def select_topic(
    callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext
) -> None:
    """
    Выбрать тематику кампании.
    """
    topic = callback_data.value
    await state.update_data(topic=topic)

    text = (
        "📝 <b>Создание кампании</b>\n\n"
        "Шаг 2 из 7: Введите заголовок рекламного сообщения.\n\n"
        "Это первая строка, которую увидят пользователи.\n"
        "📏 Длина: от 5 до 255 символов.\n\n"
        "Пример: «🔥 Скидка 50% на курс по Python!»"
    )

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
    await state.set_state(CampaignStates.waiting_header)
    await state.update_data(step="header")


@router.callback_query(CampaignStates.waiting_topic, CampaignCB.filter(F.action == "back"))
async def topic_back(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к началу.
    """
    await state.clear()
    await start_campaign_wizard(callback, state)


# ==================== ОБРАБОТКА WAITING_TITLE (ДЛЯ FLOW ЧЕРЕЗ ШАБЛОНЫ) ====================


@router.message(CampaignStates.waiting_title)
async def handle_title_input(message: Message, state: FSMContext) -> None:
    """
    Обработать название кампании (для flow через шаблоны).
    """
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return
    title = message.text.strip()

    if len(title) < 3 or len(title) > 100:
        await message.answer(
            "❌ Название должно быть от 3 до 100 символов.\n\nВведите название кампании:"
        )
        return

    await state.update_data(header=title)

    # Если текст уже задан (через шаблон) — переходим к размеру аудитории
    data = await state.get_data()
    if data.get("text"):
        text = "👥 <b>Размер аудитории</b>\n\nШаг 5 из 7: Выберите размер чатов для рассылки."
        await message.answer(text, reply_markup=get_member_count_kb())
        await state.set_state(CampaignStates.waiting_member_count)
    else:
        # Стандартный flow — идём к выбору типа текста
        # Получаем тариф пользователя
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(message.from_user.id)  # type: ignore[union-attr]
            # Получаем план пользователя
            from src.db.models.user import UserPlan

            user_plan = user.plan if isinstance(user.plan, UserPlan) else UserPlan(user.plan)  # type: ignore[union-attr]

        text = "✍️ <b>Текст кампании</b>\n\nКак вы хотите создать текст для рассылки?"
        await message.answer(text, reply_markup=get_text_type_kb(user_plan))
        await state.set_state(CampaignStates.waiting_text)


# ==================== ШАГ 2: ЗАГОЛОВОК ====================


@router.message(CampaignStates.waiting_header)
async def handle_header_input(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод заголовка.
    """
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return
    header = message.text.strip()

    if len(header) < 5:
        await message.answer(
            "❌ Заголовок слишком короткий (минимум 5 символов).\n\n"
            "Введите заголовок рекламного сообщения:"
        )
        return

    if len(header) > 255:
        await message.answer(
            "❌ Заголовок слишком длинный (максимум 255 символов).\n\n"
            "Введите заголовок рекламного сообщения:"
        )
        return

    await state.update_data(header=header)

    # Получаем тариф пользователя
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)  # type: ignore[union-attr]
        from src.db.models.user import UserPlan

        user_plan = user.plan if user and isinstance(user.plan, UserPlan) else UserPlan.FREE

    text = "✍️ <b>Текст кампании</b>\n\nШаг 3 из 7: Как вы хотите создать текст для рассылки?"

    await message.answer(text, reply_markup=get_text_type_kb(user_plan))
    await state.set_state(CampaignStates.waiting_text)
    await state.update_data(step="text_type")


# ==================== ШАГ 3: ТЕКСТ (ВЫБОР ТИПА) ====================


@router.callback_query(CampaignStates.waiting_text, CampaignCB.filter(F.action == "back"))
async def text_back(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к заголовку.
    """
    await state.set_state(CampaignStates.waiting_header)
    await state.update_data(step="header")

    text = (
        "📝 <b>Заголовок кампании</b>\n\nВведите заголовок рекламного сообщения (5-255 символов):"
    )

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())


@router.callback_query(CampaignStates.waiting_text, CampaignCB.filter(F.action == "manual_text"))
async def select_manual_text(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбран ручной ввод текста.
    """
    await state.update_data(text_type="manual")

    text = (
        "✏️ <b>Введите текст кампании</b>\n\n"
        "Шаг 3 из 7: Введите основной текст рекламного сообщения.\n\n"
        "📏 Длина: от 50 до 4000 символов.\n"
        "💡 Добавьте призыв к действию и контактную информацию."
    )

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
    await state.set_state(CampaignStates.waiting_text)
    await state.update_data(step="manual_text")


@router.callback_query(CampaignStates.waiting_text, CampaignCB.filter(F.action == "ai_locked"))
async def handle_ai_locked(callback: CallbackQuery) -> None:
    """
    Уведомить что ИИ-генерация недоступна на FREE тарифе.
    """
    await callback.answer(
        "🔒 ИИ-генерация доступна на тарифе STARTER и выше.\nПерейдите в Кабинет → Сменить тариф.",
        show_alert=True,
    )


@router.callback_query(CampaignStates.waiting_text, CampaignCB.filter(F.action == "ai_text"))
async def select_ai_text(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Выбрана ИИ-генерация текста. Проверяем тариф.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Конвертируем plan из строки в Enum если нужно
        from src.db.models.user import UserPlan

        plan = user.plan if isinstance(user.plan, UserPlan) else UserPlan(user.plan)
        if plan == UserPlan.FREE:
            await callback.answer(
                "❌ ИИ-генерация недоступна на тарифе FREE\n\n"
                "Перейдите на STARTER или выше для использования ИИ.",
                show_alert=True,
            )
            return

    await state.update_data(text_type="ai")

    text = (
        "🤖 <b>Генерация текста через ИИ</b>\n\n"
        "Шаг 3 из 7: Опишите ваш продукт или услугу.\n"
        "ИИ создаст текст за вас.\n\n"
        "💰 Стоимость генерации: <b>10₽</b>\n\n"
        "Пример описания:\n"
        "«Онлайн-курс по Python для начинающих. Длительность 3 месяца, практика, дипломный проект.»"
    )

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
    await state.set_state(CampaignStates.waiting_ai_description)
    await state.update_data(step="ai_description")


# ==================== ШАГ 3a: AI ОПИСАНИЕ ====================


@router.message(CampaignStates.waiting_ai_description)
async def handle_ai_description(message: Message, state: FSMContext) -> None:
    """
    Обработать описание для ИИ-генерации.
    """
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return
    description = message.text.strip()

    if len(description) < 10:
        await message.answer(
            "❌ Описание слишком короткое (минимум 10 символов).\n\nОпишите ваш продукт или услугу:"
        )
        return

    await state.update_data(ai_description=description)

    status_message = await message.answer("🤖 Генерирую варианты текстов...")

    try:
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(message.from_user.id)  # type: ignore[union-attr]

            if not user:
                await status_message.edit_text("❌ Пользователь не найден")
                return

            # Проверяем баланс в кредитах
            cost = 10  # 10 кредитов
            if user.credits < cost:
                await status_message.edit_text(
                    f"❌ Недостаточно кредитов.\n"
                    f"Требуется: {cost} кр, у вас: {user.credits} кр\n\n"
                    "Пополните баланс и попробуйте снова."
                )
                await state.set_state(CampaignStates.waiting_text)
                return

        # Генерируем варианты
        variants = await ai_service.generate_ab_variants(
            description=description,
            count=3,
        )

        await status_message.delete()

        # Сохраняем варианты
        await state.update_data(ai_variants=variants)

        text = "🤖 <b>Варианты текста от ИИ</b>\n\nВыберите лучший вариант:\n\n"
        for i, variant in enumerate(variants, 1):
            text += f"<b>Вариант {i}:</b>\n{variant[:300]}...\n\n"

        builder = InlineKeyboardBuilder()
        for i in range(1, 4):
            builder.button(
                text=f"Вариант {i}", callback_data=CampaignCB(action="ai_variant", value=str(i))
            )
        builder.button(text="← Назад", callback_data=CampaignCB(action="back"))
        builder.button(text="✖ Отмена", callback_data=CampaignCB(action="cancel"))
        builder.adjust(1, 1, 1)

        await message.answer(text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"AI generation error: {e}")
        await status_message.edit_text(
            f"❌ Ошибка генерации: {e}\n\nПопробуйте ещё раз или выберите ручной ввод текста."
        )
        await state.set_state(CampaignStates.waiting_ai_description)


@router.callback_query(CampaignCB.filter(F.action == "ai_variant"))
async def select_ai_variant(
    callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext
) -> None:
    """
    Выбрать вариант ИИ-текста.
    """
    variant_index = int(callback_data.value) - 1
    data = await state.get_data()
    variants = data.get("ai_variants", [])

    if not variants or variant_index >= len(variants):
        await callback.answer("❌ Вариант не найден", show_alert=True)
        return

    selected_text = variants[variant_index]
    await state.update_data(text=selected_text)

    # Переход к загрузке изображения
    await show_image_upload(callback, state)


# ==================== ШАГ 3b: РУЧНОЙ ТЕКСТ ====================


@router.message(F.text, CampaignStates.waiting_text)
async def handle_text_input(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод текста кампании.
    """
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return
    text = message.text.strip()

    data = await state.get_data()
    text_type = data.get("text_type", "manual")

    if text_type != "manual":
        return

    if len(text) < 50:
        await message.answer(
            "❌ Текст слишком короткий (минимум 50 символов).\n\nВведите текст кампании:"
        )
        return

    if len(text) > 4000:
        await message.answer(
            "❌ Текст слишком длинный (максимум 4000 символов).\n\nВведите текст кампании:"
        )
        return

    # Content filter проверка
    filter_result = content_filter_check(text)
    if not filter_result.passed:
        categories = ", ".join(filter_result.categories)
        await message.answer(
            f"⚠️ Текст содержит запрещённый контент.\n\n"
            f"Категории: {categories}\n\n"
            "Пожалуйста, измените текст:"
        )
        return

    await state.update_data(text=text)

    # Переход к загрузке изображения
    await show_image_upload(message, state)


async def show_image_upload(target: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Показать запрос на загрузку изображения.
    """
    await state.set_state(CampaignStates.waiting_image)
    await state.update_data(step="image")

    text = (
        "📷 <b>Изображение кампании</b>\n\n"
        "Шаг 4 из 7: Загрузите изображение для рекламного сообщения.\n\n"
        "📎 Изображение прикрепляется к тексту.\n"
        "⏭ Можно пропустить этот шаг."
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=get_image_upload_kb())  # type: ignore[union-attr]
    else:
        await target.answer(text, reply_markup=get_image_upload_kb())


# ==================== ШАГ 4: ИЗОБРАЖЕНИЕ ====================


@router.callback_query(CampaignStates.waiting_image, CampaignCB.filter(F.action == "image_upload"))
async def image_upload(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать загрузку изображения.
    """
    text = (
        "📷 <b>Загрузка изображения</b>\n\n"
        "Отправьте изображение для вашей кампании.\n\n"
        "💡 Изображение будет прикреплено к тексту рассылки."
    )

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
    await state.set_state(CampaignStates.waiting_image)
    await state.update_data(step="image_upload")


@router.message(CampaignStates.waiting_image, F.photo)
async def handle_image_upload(message: Message, state: FSMContext) -> None:
    """
    Обработать загруженное изображение.
    """
    # Получаем file_id самого большого фото
    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте фото.")
        return
    image_file_id = message.photo[-1].file_id
    await state.update_data(image_file_id=image_file_id)

    # Переход к выбору размера аудитории
    text = "👥 <b>Размер аудитории</b>\n\nШаг 5 из 7: Выберите размер чатов для рассылки."

    await message.answer(text, reply_markup=get_member_count_kb())
    await state.set_state(CampaignStates.waiting_member_count)
    await state.update_data(step="member_count")


@router.callback_query(CampaignStates.waiting_image, CampaignCB.filter(F.action == "image_skip"))
async def image_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Пропустить загрузку изображения.
    """
    # Переход к выбору размера аудитории
    text = "👥 <b>Размер аудитории</b>\n\nШаг 5 из 7: Выберите размер чатов для рассылки."

    await safe_callback_edit(callback, text, reply_markup=get_member_count_kb())
    await state.set_state(CampaignStates.waiting_member_count)
    await state.update_data(step="member_count")


@router.callback_query(CampaignStates.waiting_image, CampaignCB.filter(F.action == "back"))
async def image_back(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к тексту.
    """
    data = await state.get_data()
    text_type = data.get("text_type", "manual")

    if text_type == "ai":
        await state.set_state(CampaignStates.waiting_ai_description)
        text = "🤖 <b>Описание для ИИ</b>\n\nОпишите ваш продукт или услугу:"
    else:
        await state.set_state(CampaignStates.waiting_text)
        text = "✏️ <b>Текст кампании</b>\n\nВведите текст кампании:"

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
    await state.update_data(step="text_type" if text_type == "ai" else "manual_text")


# ==================== ШАГ 5: РАЗМЕР АУДИТОРИИ ====================


@router.callback_query(CampaignStates.waiting_member_count, CampaignCB.filter(F.action == "back"))
async def member_count_back(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к изображению.
    """
    await show_image_upload(callback, state)


@router.callback_query(
    CampaignStates.waiting_member_count, CampaignCB.filter(F.action == "members")
)
async def select_member_count(
    callback: CallbackQuery, callback_data: CampaignCB, state: FSMContext
) -> None:
    """
    Выбрать размер аудитории.
    """
    value = callback_data.value
    if value == "any":
        min_members = 0
        max_members = 1000000
    else:
        min_str, max_str = value.split("_")
        min_members = int(min_str)
        max_members = int(max_str)

    await state.update_data(
        min_members=min_members,
        max_members=max_members,
    )

    text = "⏰ <b>Расписание запуска</b>\n\nШаг 6 из 7: Когда запустить кампанию?"

    await safe_callback_edit(callback, text, reply_markup=get_schedule_kb())
    await state.set_state(CampaignStates.waiting_schedule)
    await state.update_data(step="schedule")


# ==================== ШАГ 6: РАСПИСАНИЕ ====================


@router.callback_query(CampaignStates.waiting_schedule, CampaignCB.filter(F.action == "back"))
async def schedule_back(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к выбору размера аудитории.
    """
    text = "👥 <b>Размер аудитории</b>\n\nВыберите размер чатов для рассылки:"

    await safe_callback_edit(callback, text, reply_markup=get_member_count_kb())
    await state.set_state(CampaignStates.waiting_member_count)
    await state.update_data(step="member_count")


@router.callback_query(
    CampaignStates.waiting_schedule, CampaignCB.filter(F.action == "schedule_now")
)
async def schedule_now(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запустить кампанию сейчас.
    """
    await state.update_data(schedule="now", scheduled_at=None)
    await show_confirmation(callback, state)


@router.callback_query(
    CampaignStates.waiting_schedule, CampaignCB.filter(F.action == "schedule_later")
)
async def schedule_later(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запланировать кампанию на позже.
    """
    text = (
        "⏰ <b>Запланировать запуск</b>\n\n"
        "Отправьте дату и время запуска в формате:\n"
        "ГГГГ-ММ-ДД ЧЧ:ММ\n\n"
        "Пример: 2026-03-01 15:30"
    )

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
    await state.set_state(CampaignStates.waiting_schedule)
    await state.update_data(step="schedule_datetime")


@router.message(CampaignStates.waiting_schedule)
async def handle_schedule_datetime(message: Message, state: FSMContext) -> None:
    """
    Обработать дату и время запуска.
    """
    if not message.text:
        await message.answer("Пожалуйста, введите дату и время.")
        return
    text = message.text.strip()

    # Парсинг даты
    try:
        scheduled_at = datetime.strptime(text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\n\n"
            "Используйте формат: ГГГГ-ММ-ДД ЧЧ:ММ\n"
            "Пример: 2026-03-01 15:30"
        )
        return

    if scheduled_at <= datetime.now():
        await message.answer("❌ Дата должна быть в будущем.\n\nВведите дату и время запуска:")
        return

    await state.update_data(scheduled_at=scheduled_at.isoformat(), schedule="later")
    await show_confirmation(message, state)


# ==================== ШАГ 7: ПОДТВЕРЖДЕНИЕ ====================


async def show_confirmation(target: Message | CallbackQuery, state: FSMContext) -> None:
    """
    Показать карточку подтверждения кампании.
    """
    await state.set_state(CampaignStates.waiting_confirm)
    await state.update_data(step="confirm")

    data = await state.get_data()

    topic = data.get("topic", "Не указана")
    header = data.get("header", "Без заголовка")
    text = data.get("text", "")[:300]
    has_image = "📷" if data.get("image_file_id") else "❌"
    min_members = data.get("min_members", 0)
    max_members = data.get("max_members", 1000000)
    schedule = (
        "Немедленно" if data.get("schedule") == "now" else data.get("scheduled_at", "Не указано")
    )

    confirmation_text = (
        "✅ <b>Подтверждение кампании</b>\n\n"
        f"📌 <b>Тема:</b> {topic}\n"
        f"📰 <b>Заголовок:</b> {header}\n"
        f"📝 <b>Текст:</b> {text}...\n"
        f"📷 <b>Изображение:</b> {has_image}\n"
        f"👥 <b>Аудитория:</b> {min_members}-{max_members} участников\n"
        f"⏰ <b>Запуск:</b> {schedule}\n\n"
        "Проверьте информацию и выберите действие:"
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(confirmation_text, reply_markup=get_campaign_confirm_kb())  # type: ignore[union-attr]
    else:
        await target.answer(confirmation_text, reply_markup=get_campaign_confirm_kb())


@router.callback_query(CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "back"))
async def confirm_back(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Вернуться к расписанию.
    """
    text = "⏰ <b>Расписание запуска</b>\n\nКогда запустить кампанию?"

    await safe_callback_edit(callback, text, reply_markup=get_schedule_kb())
    await state.set_state(CampaignStates.waiting_schedule)
    await state.update_data(step="schedule")


@router.callback_query(
    CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "confirm_edit")
)
async def confirm_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Изменить текст кампании.
    """
    text = "✏️ <b>Редактирование текста</b>\n\nВведите новый текст кампании:"

    await safe_callback_edit(callback, text, reply_markup=get_campaign_step_kb())
    await state.set_state(CampaignStates.waiting_text)
    await state.update_data(step="manual_text")


@router.callback_query(
    CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "confirm_draft")
)
async def confirm_draft(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Сохранить кампанию как черновик.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        data = await state.get_data()
        campaign_repo = CampaignRepository(session)

        # Создаём кампанию в статусе DRAFT
        campaign = await campaign_repo.create(
            {
                "user_id": user.id,
                "title": data.get("header", "Черновик"),
                "topic": data.get("topic"),
                "header": data.get("header"),
                "text": data.get("text", ""),
                "image_file_id": data.get("image_file_id"),
                "ai_description": data.get("ai_description"),
                "status": CampaignStatus.DRAFT,
                "filters_json": {
                    "topics": [data.get("topic")],
                    "min_members": data.get("min_members", 0),
                    "max_members": data.get("max_members", 1000000),
                },
                "scheduled_at": None,
            }
        )

    await state.clear()

    text = (
        f"💾 <b>Кампания сохранена в черновиках!</b>\n\n"
        f"📋 {campaign.title}\n\n"
        f"Вы можете запустить её позже из личного кабинета."
    )

    await safe_callback_edit(callback, text, reply_markup=get_main_menu(user.credits, user.id))


@router.callback_query(
    CampaignStates.waiting_confirm, CampaignCB.filter(F.action == "confirm_launch")
)
async def confirm_launch(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Запустить кампанию.
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
        campaign_repo = CampaignRepository(session)

        # Проверяем лимит кампаний
        campaign_count = await campaign_repo.get_user_campaigns_count(user.id)
        if campaign_count >= user.get_campaign_limit():
            await callback.answer(
                f"❌ Превышен лимит кампаний для вашего тарифа: {user.get_campaign_limit()}\n"
                "Перейдите в кабинет для смены тарифа.",
                show_alert=True,
            )
            return

        # Парсим scheduled_at
        scheduled_at_str = data.get("scheduled_at")
        scheduled_at = None
        if scheduled_at_str:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)

        # Проверяем уведомления — если выключены, спрашиваем перед запуском
        if not user.notifications_enabled and not scheduled_at:
            # Сохраняем данные в state и показываем запрос
            await safe_callback_edit(callback, "🚀 Кампания готова к запуску!\n\n"
                "📬 Хотите получать уведомления о статусе кампании?\n"
                "(паузы, ошибки, завершение)",
                reply_markup=get_notifications_prompt_kb(),
            )
            return

        # Запускаем кампанию (создание и отправка)
        await _do_launch_campaign(callback, state, session, user, data, campaign_repo, scheduled_at)


async def _do_launch_campaign(
    callback: CallbackQuery,
    state: FSMContext,
    session,
    user,
    data: dict,
    campaign_repo,
    scheduled_at=None,
) -> None:
    """
    Приватная функция для фактического запуска кампании.
    Вызывается из confirm_launch или после включения уведомлений.
    """

    # Создаём кампанию
    campaign = await campaign_repo.create(
        {
            "user_id": user.id,
            "title": data.get("header", "Без названия"),
            "topic": data.get("topic"),
            "header": data.get("header"),
            "text": data.get("text", ""),
            "image_file_id": data.get("image_file_id"),
            "ai_description": data.get("ai_description"),
            "status": CampaignStatus.QUEUED if scheduled_at else CampaignStatus.RUNNING,
            "filters_json": {
                "topics": [data.get("topic")],
                "min_members": data.get("min_members", 0),
                "max_members": data.get("max_members", 1000000),
            },
            "scheduled_at": scheduled_at,
        }
    )

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

    await safe_callback_edit(callback, text, reply_markup=get_main_menu(user.credits, user.id))


# ==================== ОТМЕНА ====================


@router.callback_query(CampaignCB.filter(F.action == "cancel"))
async def cancel_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отменить создание кампании.
    """
    await state.clear()

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

    text = "✖ Создание кампании отменено."

    if user:
        await safe_callback_edit(callback, text, reply_markup=get_main_menu(user.credits, user.id))
    else:
        await safe_callback_edit(callback, text)
        await callback.answer("❌ Пользователь не найден. Нажмите /start")


@router.callback_query(
    CampaignStates.waiting_confirm, CabinetCB.filter(F.action == "enable_notif_and_launch")
)
async def enable_notif_and_launch(callback: CallbackQuery, state: FSMContext) -> None:
    """Включить уведомления и запустить кампанию."""
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        await user_repo.toggle_notifications(callback.from_user.id)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        data = await state.get_data()
        campaign_repo = CampaignRepository(session)

    await _do_launch_campaign(callback, state, session, user, data, campaign_repo)


@router.callback_query(
    CampaignStates.waiting_confirm, CabinetCB.filter(F.action == "launch_without_notif")
)
async def launch_without_notif(callback: CallbackQuery, state: FSMContext) -> None:
    """Запустить кампанию без включения уведомлений."""
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        data = await state.get_data()
        campaign_repo = CampaignRepository(session)

    await _do_launch_campaign(callback, state, session, user, data, campaign_repo)


# ─────────────────────────────────────────────
# Запрос отзывов после завершения кампании (Спринт 2)
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("review_request:"))
async def handle_review_request(callback: CallbackQuery) -> None:
    """
    Обработка кнопки запроса отзыва.
    """
    if callback.message is None or isinstance(callback.message, Message):
        return

    placement_id = int((callback.data or "").split(":")[1])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐️⭐️⭐️⭐️⭐️ (5)", callback_data=f"review_submit:{placement_id}:5"),
            ],
            [
                InlineKeyboardButton(text="⭐️⭐️⭐️⭐️ (4)", callback_data=f"review_submit:{placement_id}:4"),
            ],
            [
                InlineKeyboardButton(text="⭐️⭐️⭐️ (3)", callback_data=f"review_submit:{placement_id}:3"),
            ],
            [
                InlineKeyboardButton(text="⭐️⭐️ (2)", callback_data=f"review_submit:{placement_id}:2"),
            ],
            [
                InlineKeyboardButton(text="⭐️ (1)", callback_data=f"review_submit:{placement_id}:1"),
            ],
            [
                InlineKeyboardButton(text="❌ Пропустить", callback_data="review_skip"),
            ],
        ]
    )

    await safe_callback_edit(
        callback,
        "📝 <b>Оставьте отзыв о размещении</b>\n\n"
        "Ваше мнение поможет улучшить платформу!\n\n"
        "Выберите оценку:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("review_submit:"))
async def handle_review_submit(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Отправка отзыва с оценкой.
    """
    if callback.message is None or isinstance(callback.message, Message):
        return

    data_parts = (callback.data or "").split(":")
    if len(data_parts) != 3:
        await callback.answer("❌ Неверный формат", show_alert=True)
        return

    placement_id = int(data_parts[1])
    score = int(data_parts[2])

    # Сохраняем оценку в FSM для последующей отправки
    await state.update_data(
        review_placement_id=placement_id,
        review_score=score,
    )

    await callback.answer(f"✅ Оценка {score} принята!")

    # Здесь будет вызов review_service.create_review()
    # Для now просто уведомляем
    await safe_callback_edit(
        callback,
        "✅ <b>Спасибо за отзыв!</b>\n\n"
        f"Вы поставили оценку: {score} ⭐\n\n"
        "Ваше мнение поможет улучшить платформу.",
        parse_mode="HTML",
    )
    await state.clear()


@router.callback_query(F.data == "review_skip")
async def handle_review_skip(callback: CallbackQuery) -> None:
    """
    Пропуск отзыва.
    """
    if callback.message is None or isinstance(callback.message, Message):
        return

    await safe_callback_edit(
        callback,
        "ℹ️ <b>Отзыв пропущен</b>\n\n"
        "Вы всегда можете оставить отзыв позже через /my_channels",
        parse_mode="HTML",
    )
