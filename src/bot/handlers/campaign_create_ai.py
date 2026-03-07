"""
Handlers для создания кампании с AI генерацией текста.
Новый флоу: Стиль → Категория → Описание → Название → AI генерация → Выбор → Настройки → Запуск
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.keyboards.campaign_ai import (
    AIEditCB,
    AIVariantCB,
    CampaignCreateCB,
    CAMPAIGN_CATEGORIES,
    TEXT_STYLES,
    get_ai_category_keyboard,
    get_ai_style_keyboard,
    get_ai_variants_keyboard,
    get_campaign_editor_keyboard,
)
from src.bot.states.campaign_create import CampaignCreateState
from src.bot.utils.safe_callback import safe_callback_edit
from src.core.services.ai_service import AIService
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


# ──────────────────────────────────────────────────────────────
# Шаг 1: Начало - выбор стиля текста
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step == "start"))
async def start_campaign_create(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать создание кампании с AI."""
    await state.clear()

    text = (
        "🤖 <b>Создание кампании с AI</b>\n\n"
        "Я помогу создать эффективную рекламную кампанию!\n\n"
        "<b>План:</b>\n"
        "1️⃣ Выберите стиль текста\n"
        "2️⃣ Выберите категорию кампании\n"
        "3️⃣ Опишите продукт/услугу\n"
        "4️⃣ Придумайте название кампании\n"
        "5️⃣ AI сгенерирует 3 варианта текста\n"
        "6️⃣ Выберите лучший или отредактируйте\n"
        "7️⃣ Добавьте ссылку и изображение\n"
        "8️⃣ Настройте таргетинг и бюджет\n"
        "9️⃣ Запустите кампанию!\n\n"
        "<b>Начнём с выбора стиля текста:</b>"
    )

    await safe_callback_edit(callback, text, reply_markup=get_ai_style_keyboard())
    await state.set_state(CampaignCreateState.selecting_style)


# ──────────────────────────────────────────────────────────────
# Шаг 2: Выбор стиля текста
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step.startswith("style_")))
async def style_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Стиль выбран — переходим к выбору категории."""
    if not callback.data:
        return
    
    style = callback.data.split("_")[-1]
    style_name = TEXT_STYLES.get(style, style)
    
    logger.info(f"style_selected: style={style}, name={style_name}")
    await state.update_data(style=style, style_name=style_name)
    await state.set_state(CampaignCreateState.selecting_category)

    text = (
        f"✅ <b>Стиль: {style_name}</b>\n\n"
        "Теперь выберите <b>категорию кампании</b>.\n"
        "Это поможет AI подобрать правильные слова и акценты.\n\n"
        "Если не нашли подходящую — нажмите «Своя категория»:"
    )

    await safe_callback_edit(callback, text, reply_markup=get_ai_category_keyboard())


@router.callback_query(CampaignCreateCB.filter(F.step == "custom_category"))
async def custom_category_requested(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет ввести свою категорию."""
    await state.set_state(CampaignCreateState.entering_custom_category)
    
    text = (
        "✍️ <b>Введите свою категорию</b>\n\n"
        "Например:\n"
        "• IT и стартапы\n"
        "• Онлайн-школы\n"
        "• Криптовалюты\n"
        "• Психология бизнеса\n\n"
        "👇 Напишите категорию ниже:"
    )
    
    await safe_callback_edit(callback, text)
    
    # Кнопка назад
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=CampaignCreateCB(step="back_to_category").pack())]
        ]
    )
    await callback.message.answer("Или выберите из списка:", reply_markup=keyboard)


@router.message(CampaignCreateState.entering_custom_category)
async def process_custom_category(message: Message, state: FSMContext) -> None:
    """Обработка введённой пользователем категории."""
    custom_category = message.text.strip()
    if len(custom_category) > 50:
        await message.answer("❌ Категория слишком длинная. Максимум 50 символов.")
        return
    
    logger.info(f"custom_category: {custom_category}")
    await state.update_data(category="custom", custom_category=custom_category)
    await state.set_state(CampaignCreateState.waiting_for_description)
    
    text = (
        f"✅ <b>Категория: {custom_category}</b>\n\n"
        "Теперь <b>опишите ваш продукт или услугу</b>.\n\n"
        "<b>Что указать:</b>\n"
        "• Что вы предлагаете\n"
        "• Ключевые преимущества\n"
        "• Цену или акции (если есть)\n\n"
        "👇 Напишите описание ниже:"
    )
    
    await message.answer(text)


@router.callback_query(CampaignCreateCB.filter(F.step.startswith("category_")))
async def category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Категория выбрана — запрашиваем описание."""
    if not callback.data:
        return
    
    category = callback.data.split("_")[-1]
    category_name = CAMPAIGN_CATEGORIES.get(category, category)
    
    logger.info(f"category_selected: category={category}, name={category_name}")
    await state.update_data(category=category, category_name=category_name)
    await state.set_state(CampaignCreateState.waiting_for_description)

    text = (
        f"✅ <b>Категория: {category_name}</b>\n\n"
        "Теперь <b>опишите ваш продукт или услугу</b>.\n\n"
        "<b>Что указать:</b>\n"
        "• Что вы предлагаете\n"
        "• Ключевые преимущества\n"
        "• Цену или акции (если есть)\n\n"
        "👇 Напишите описание ниже:"
    )

    await safe_callback_edit(callback, text)


# ──────────────────────────────────────────────────────────────
# Шаг 3: Описание продукта
# ──────────────────────────────────────────────────────────────

@router.message(CampaignCreateState.waiting_for_description)
async def process_description(message: Message, state: FSMContext) -> None:
    """Получили описание — запрашиваем название кампании."""
    description = message.text.strip()
    if len(description) < 20:
        await message.answer("❌ Описание слишком короткое. Минимум 20 символов.")
        return
    
    logger.info(f"description: {description[:100]}...")
    await state.update_data(description=description)
    await state.set_state(CampaignCreateState.waiting_for_campaign_name)
    
    text = (
        "✅ <b>Описание принято</b>\n\n"
        "Теперь придумайте <b>название для кампании</b>.\n"
        "Это поможет вам отличать её от других в списке.\n\n"
        "Например:\n"
        "• «Весенняя распродажа 2026»\n"
        "• «Запуск курса по маркетингу»\n"
        "• «Black Friday — магазин обуви»\n\n"
        "👇 Напишите название ниже:"
    )
    
    await message.answer(text)


# ──────────────────────────────────────────────────────────────
# Шаг 4: Название кампании
# ──────────────────────────────────────────────────────────────

@router.message(CampaignCreateState.waiting_for_campaign_name)
async def process_campaign_name(message: Message, state: FSMContext) -> None:
    """Получили название — генерируем тексты."""
    campaign_name = message.text.strip()
    if len(campaign_name) < 3:
        await message.answer("❌ Название слишком короткое. Минимум 3 символа.")
        return
    
    if len(campaign_name) > 100:
        await message.answer("❌ Название слишком длинное. Максимум 100 символов.")
        return
    
    logger.info(f"campaign_name: {campaign_name}")
    await state.update_data(campaign_name=campaign_name)
    await state.set_state(CampaignCreateState.selecting_variant)
    
    # Генерация текстов через AI
    await message.answer("🤖 <b>AI генерирует варианты текста...</b>\n\nЭто займёт несколько секунд.")
    
    data = await state.get_data()
    style = data.get("style", "business")
    category = data.get("category", "other")
    category_name = data.get("category_name", category)
    custom_category = data.get("custom_category")
    description = data.get("description", "")
    
    # Формируем промпт для AI
    actual_category = custom_category if category == "custom" else category_name
    prompt = (
        f"Создай рекламный текст для Telegram-канала.\n\n"
        f"Категория: {actual_category}\n"
        f"Описание продукта:\n{description}\n\n"
        f"Требования:\n"
        f"- Длина 300-600 символов\n"
        f"- Используй эмодзи уместно\n"
        f"- Добавь призыв к действию\n"
        f"- Стиль: {TEXT_STYLES.get(style, 'универсальный')}"
    )
    
    try:
        ai_service = AIService()
        # Генерируем 3 варианта
        variants = []
        for i in range(3):
            variant = await ai_service.generate(
                prompt=prompt,
                user_plan="business",  # Используем PRO модель
                use_cache=False,
            )
            variants.append(variant)
        
        logger.info(f"AI generated {len(variants)} variants")
        
        # Показываем варианты
        text = (
            "✨ <b>AI сгенерировал 3 варианта текста</b>\n\n"
            "Выберите лучший или попросите сгенерировать заново:\n\n"
        )
        
        for i, variant in enumerate(variants, 1):
            preview = variant[:150].replace("\n", " ") + "..." if len(variant) > 150 else variant
            text += f"<b>Вариант {i}:</b>\n{preview}\n\n"
        
        await message.answer(text, reply_markup=get_ai_variants_keyboard(variants))
        
        # Сохраняем варианты в state
        await state.update_data(ai_variants=variants)
        
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        await message.answer(
            "❌ <b>Ошибка генерации</b>\n\n"
            "Не удалось сгенерировать текст. Попробуйте ещё раз или напишите текст вручную."
        )


# ──────────────────────────────────────────────────────────────
# Шаг 5: Выбор варианта текста
# ──────────────────────────────────────────────────────────────

@router.callback_query(AIVariantCB.filter())
async def select_variant(callback: CallbackQuery, callback_data: AIVariantCB, state: FSMContext) -> None:
    """Выбран вариант текста — переходим к редактору."""
    variant_index = callback_data.variant_index
    logger.info(f"select_variant: index={variant_index}")
    
    data = await state.get_data()
    variants = data.get("ai_variants", [])
    
    if variant_index >= len(variants):
        await callback.answer("❌ Вариант не найден", show_alert=True)
        return
    
    selected_text = variants[variant_index]
    await state.update_data(selected_variant_index=variant_index, text=selected_text)
    await state.set_state(CampaignCreateState.editing_text)
    
    text = (
        "✏️ <b>Редактирование текста</b>\n\n"
        "Вы можете изменить текст или добавить дополнительные элементы:\n\n"
        f"<b>Текущий текст:</b>\n{selected_text[:500]}{'...' if len(selected_text) > 500 else ''}"
    )
    
    has_url = bool(data.get("url"))
    has_image = bool(data.get("image_file_id"))
    
    await safe_callback_edit(
        callback,
        text,
        reply_markup=get_campaign_editor_keyboard(selected_text, has_url, has_image)
    )


# ──────────────────────────────────────────────────────────────
# Шаг 6: Редактирование текста
# ──────────────────────────────────────────────────────────────

@router.callback_query(AIEditCB.filter(F.action == "edit_text"))
async def edit_text_requested(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос на редактирование текста."""
    await state.set_state(CampaignCreateState.editing_text)
    await callback.answer("👇 Отправьте новый текст ниже:")


@router.message(CampaignCreateState.editing_text)
async def process_edited_text(message: Message, state: FSMContext) -> None:
    """Получили отредактированный текст."""
    new_text = message.text.strip()
    if len(new_text) < 50:
        await message.answer("❌ Текст слишком короткий. Минимум 50 символов.")
        return
    
    logger.info(f"edited_text: {new_text[:100]}...")
    await state.update_data(text=new_text)
    await state.set_state(CampaignCreateState.waiting_for_url)
    
    text = (
        "✅ <b>Текст обновлён</b>\n\n"
        "Хотите добавить <b>ссылку</b> на продукт/услугу?\n\n"
        "👇 Отправьте URL или нажмите «Пропустить»:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=CampaignCreateCB(step="skip_url").pack())]
        ]
    )
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(CampaignCreateCB.filter(F.step == "skip_url"))
async def skip_url(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропустить добавление URL."""
    await state.set_state(CampaignCreateState.waiting_for_image)
    
    text = (
        "✅ <b>Без ссылки</b>\n\n"
        "Хотите добавить <b>изображение</b> к посту?\n\n"
        "👇 Отправьте фото или нажмите «Пропустить»:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=CampaignCreateCB(step="skip_image").pack())]
        ]
    )
    
    await safe_callback_edit(callback, text, reply_markup=keyboard)


# ──────────────────────────────────────────────────────────────
# Шаг 7: Добавление URL
# ──────────────────────────────────────────────────────────────

@router.message(CampaignCreateState.waiting_for_url)
async def process_url(message: Message, state: FSMContext) -> None:
    """Получили URL."""
    url = message.text.strip()
    if not url.startswith(("http://", "https://", "t.me/")):
        await message.answer("❌ Неверный формат URL. Должен начинаться с http://, https:// или t.me/")
        return
    
    logger.info(f"url: {url}")
    await state.update_data(url=url)
    await state.set_state(CampaignCreateState.waiting_for_image)
    
    text = (
        f"✅ <b>Ссылка добавлена:</b> {url}\n\n"
        "Хотите добавить <b>изображение</b> к посту?\n\n"
        "👇 Отправьте фото или нажмите «Пропустить»:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=CampaignCreateCB(step="skip_image").pack())]
        ]
    )
    
    await message.answer(text, reply_markup=keyboard)


# ──────────────────────────────────────────────────────────────
# Шаг 8: Добавление изображения
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step == "skip_image"))
async def skip_image(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропустить добавление изображения — переход к настройкам."""
    await state.set_state(CampaignCreateState.selecting_audience)
    
    text = (
        "⚙️ <b>Настройки кампании</b>\n\n"
        "Теперь настроим таргетинг и бюджет.\n\n"
        "<b>Выберите аудитории для показа:</b>"
    )
    
    # TODO: Добавить клавиатуру с аудиториями
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📡 Все доступные каналы", callback_data=CampaignCreateCB(step="audience_all").pack())],
            [InlineKeyboardButton(text="🎯 Выбрать по категориям", callback_data=CampaignCreateCB(step="audience_categories").pack())],
        ]
    )
    
    await safe_callback_edit(callback, text, reply_markup=keyboard)


@router.message(CampaignCreateState.waiting_for_image)
async def process_image(message: Message, state: FSMContext) -> None:
    """Получили изображение."""
    if not message.photo:
        await message.answer("❌ Это не фото. Отправьте изображение или нажмите «Пропустить»:")
        return
    
    # Берём фото наилучшего качества
    image_file_id = message.photo[-1].file_id
    logger.info(f"image_file_id: {image_file_id}")
    await state.update_data(image_file_id=image_file_id)
    await state.set_state(CampaignCreateState.selecting_audience)
    
    text = (
        "✅ <b>Изображение добавлено</b>\n\n"
        "<b>Настройки кампании</b>\n\n"
        "Выберите аудитории для показа:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📡 Все доступные каналы", callback_data=CampaignCreateCB(step="audience_all").pack())],
            [InlineKeyboardButton(text="🎯 Выбрать по категориям", callback_data=CampaignCreateCB(step="audience_categories").pack())],
        ]
    )
    
    await message.answer(text, reply_markup=keyboard)


# ──────────────────────────────────────────────────────────────
# Шаг 9: Настройки аудитории (заглушка)
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step.startswith("audience_")))
async def select_audience(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрана аудитория — переходим к бюджету."""
    audience = callback.data.split("_")[-1]
    logger.info(f"audience: {audience}")
    await state.update_data(audience=audience)
    await state.set_state(CampaignCreateState.setting_budget)
    
    text = (
        "💰 <b>Настройте бюджет</b>\n\n"
        "Укажите максимальную сумму для кампании:\n\n"
        "👇 Введите сумму в кредитах:"
    )
    
    await safe_callback_edit(callback, text)


# ──────────────────────────────────────────────────────────────
# Шаг 10: Настройка бюджета (заглушка)
# ──────────────────────────────────────────────────────────────

@router.message(CampaignCreateState.setting_budget)
async def process_budget(message: Message, state: FSMContext) -> None:
    """Получили бюджет."""
    try:
        budget = int(message.text.strip())
        if budget < 100:
            await message.answer("❌ Минимальный бюджет — 100 кредитов.")
            return
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    
    logger.info(f"budget: {budget}")
    await state.update_data(budget=budget)
    await state.set_state(CampaignCreateState.setting_schedule)
    
    text = (
        "📅 <b>Когда запустить кампанию?</b>\n\n"
        "Выберите вариант:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Запустить сейчас", callback_data=CampaignCreateCB(step="schedule_now").pack())],
            [InlineKeyboardButton(text="⏰ Запланировать", callback_data=CampaignCreateCB(step="schedule_later").pack())],
        ]
    )
    
    await message.answer(text, reply_markup=keyboard)


# ──────────────────────────────────────────────────────────────
# Шаг 11: Расписание (заглушка)
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step == "schedule_now"))
async def schedule_now(callback: CallbackQuery, state: FSMContext) -> None:
    """Запустить сейчас."""
    await state.update_data(schedule="now")
    await final_create_campaign(callback, state)


@router.callback_query(CampaignCreateCB.filter(F.step == "schedule_later"))
async def schedule_later(callback: CallbackQuery, state: FSMContext) -> None:
    """Запланировать на потом."""
    # TODO: Реализовать выбор даты/времени
    await callback.answer("🚧 Функция в разработке. Запускаем сейчас.", show_alert=True)
    await state.update_data(schedule="now")
    await final_create_campaign(callback, state)


# ──────────────────────────────────────────────────────────────
# Финальное создание кампании
# ──────────────────────────────────────────────────────────────

async def final_create_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """Финальное создание кампании."""
    data = await state.get_data()
    logger.info(f"final_create_campaign: state_data={data}")

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        campaign_repo = CampaignRepository(session)

        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Собираем данные кампании
        campaign_name = data.get("campaign_name", "AI кампания")
        text = data.get("text", "")
        url = data.get("url")
        image_file_id = data.get("image_file_id")
        category = data.get("category", "other")
        custom_category = data.get("custom_category")
        budget = data.get("budget", 0)
        
        # Формируем filters_json
        actual_category = custom_category if category == "custom" else CAMPAIGN_CATEGORIES.get(category, category)
        filters_json = {
            "categories": [actual_category],
            "budget": budget,
        }

        # Создаем кампанию
        campaign = await campaign_repo.create(
            {
                "user_id": user.id,
                "title": campaign_name,
                "text": text,
                "topic": actual_category,
                "header": url,
                "image_file_id": image_file_id,
                "status": "draft",
                "filters_json": filters_json,
                "cost": budget,
            }
        )

        # Коммитим сессию чтобы кампания сохранилась в БД
        await session.commit()

        await state.clear()

        success_text = (
            f"✅ <b>Кампания создана!</b>\n\n"
            f"<b>ID:</b> {campaign.id}\n"
            f"<b>Название:</b> {campaign_name}\n"
            f"<b>Категория:</b> {actual_category}\n"
            f"<b>Бюджет:</b> {budget} кр\n"
            f"<b>Статус:</b> Черновик\n\n"
            "Теперь вы можете:\n"
            "• Запустить кампанию из раздела «Мои кампании»\n"
            "• Отредактировать настройки\n"
            "• Выбрать чаты для рассылки"
        )

        from src.bot.keyboards.main_menu import MainMenuCB

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Мои кампании",
                        callback_data=MainMenuCB(action="my_campaigns").pack(),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 В меню", callback_data=MainMenuCB(action="main_menu").pack()
                    )
                ],
            ]
        )

        await safe_callback_edit(callback, success_text, reply_markup=keyboard)


# ──────────────────────────────────────────────────────────────
# Обработчик кнопки "Написать свой текст"
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step == "manual_text"))
async def manual_text_requested(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет написать текст вручную."""
    await state.set_state(CampaignCreateState.editing_text)
    
    text = (
        "✏️ <b>Ручное создание текста</b>\n\n"
        "Напишите текст рекламного поста.\n\n"
        "<b>Рекомендации:</b>\n"
        "• Длина: 300-600 символов\n"
        "• Добавьте эмодзи\n"
        "• Включите призыв к действию\n\n"
        "👇 Отправьте текст ниже:"
    )
    
    await safe_callback_edit(callback, text)
