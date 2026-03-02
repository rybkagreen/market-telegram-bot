"""
Handlers для создания кампании с AI генерацией текста.
"""

import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.campaign_ai import (
    AIVariantCB,
    AIEditCB,
    CampaignCreateCB,
    get_ai_topic_keyboard,
    get_ai_variants_keyboard,
    get_campaign_editor_keyboard,
    get_quick_campaign_keyboard,
)
from src.bot.states.campaign_create import CampaignCreateState
from src.core.services.ai_service import AIService
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.services import get_user_service

logger = logging.getLogger(__name__)

router = Router()


# ──────────────────────────────────────────────────────────────
# Начало создания кампании
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step == "start"))
async def start_campaign_create(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать создание кампании с AI."""
    await state.clear()
    
    text = (
        "🤖 <b>Создание кампании с AI</b>\n\n"
        "Я помогу создать продающий текст для вашей кампании!\n\n"
        "<b>Как это работает:</b>\n"
        "1️⃣ Выберите тематику\n"
        "2️⃣ Опишите продукт/услугу\n"
        "3️⃣ AI сгенерирует 3 варианта текста\n"
        "4️⃣ Выберите лучший или отредактируйте\n"
        "5️⃣ Добавьте ссылку и изображение (опционально)\n"
        "6️⃣ Запустите кампанию!\n\n"
        "<b>Тематика влияет на стиль текста:</b>\n"
        "🎓 Образование — мотивирующий, с акцентом на результат\n"
        "👗 Розница — эмоциональный, с акцентом на выгоду\n"
        "💰 Финансы — профессиональный, но доступный\n"
        "☕ Другое — универсальный стиль"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_ai_topic_keyboard(),
    )


# ──────────────────────────────────────────────────────────────
# Выбор тематики
# ──────────────────────────────────────────────────────────────

@router.callback_query(CampaignCreateCB.filter(F.step.startswith("topic_")))
async def topic_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Тематика выбрана — запрашиваем описание."""
    topic = callback.data.split("_")[-1]
    await state.update_data(topic=topic)
    await state.set_state(CampaignCreateState.waiting_for_description)
    
    topic_names = {
        "education": "🎓 Образование",
        "retail": "👗 Розница",
        "finance": "💰 Финансы",
        "default": "☕ Другое",
    }
    
    text = (
        f"✅ <b>Тематика: {topic_names.get(topic, '☕ Другое')}</b>\n\n"
        "Теперь <b>опишите ваш продукт или услугу</b>.\n\n"
        "<b>Что указать:</b>\n"
        "• Что вы предлагаете\n"
        "• Ключевые преимущества\n"
        "• Цену или акции (если есть)\n"
        "• Любую важную информацию\n\n"
        "<i>Пример:</i>\n"
        "<i>«Онлайн-курс по интернет-маркетингу. 2 месяца, сертификат, трудоустройство. Цена 49900 руб.»</i>\n\n"
        "👇 Напишите описание ниже:"
    )
    
    await callback.message.edit_text(text)


@router.message(CampaignCreateState.waiting_for_description)
async def process_description(message: Message, state: FSMContext) -> None:
    """Получили описание — генерируем варианты."""
    description = message.text
    await state.update_data(description=description)
    
    # Показываем сообщение о генерации
    wait_message = await message.answer("⏳ Генерирую варианты текстов...")
    
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        topic = data.get("topic", "default")
        
        # Генерируем 3 варианта
        ai_service = AIService()
        variants = await ai_service.generate_ab_variants(
            description=description,
            user_plan="free",
            count=3,
            topic=topic,
        )
        
        await wait_message.delete()
        
        if not variants:
            await message.answer("❌ Не удалось сгенерировать тексты. Попробуйте еще раз.")
            await state.clear()
            return
        
        # Сохраняем варианты
        await state.update_data(variants=variants)
        await state.set_state(CampaignCreateState.selecting_variant)
        
        # Показываем варианты
        text = (
            "✨ <b>AI сгенерировал 3 варианта текста!</b>\n\n"
            "Выберите понравившийся вариант или отредактируйте любой:\n"
        )
        
        for i, variant in enumerate(variants, 1):
            preview = variant[:150].replace('\n', ' ') + "..." if len(variant) > 150 else variant
            text += f"\n<b>📝 Вариант {i}:</b>\n<i>{preview}</i>\n"
        
        await message.answer(
            text,
            reply_markup=get_ai_variants_keyboard(variants, topic),
        )
        
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        await wait_message.delete()
        await message.answer(f"❌ Ошибка генерации: {e}\nПопробуйте еще раз.")
        await state.clear()


# ──────────────────────────────────────────────────────────────
# Выбор варианта
# ──────────────────────────────────────────────────────────────

@router.callback_query(AIVariantCB.filter())
async def variant_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Вариант выбран — переходим к редактированию."""
    callback_data = AIVariantCB.unpack(callback.data)
    variant_index = callback_data.variant_index
    
    data = await state.get_data()
    variants = data.get("variants", [])
    
    if variant_index >= len(variants):
        await callback.answer("❌ Вариант не найден", show_alert=True)
        return
    
    selected_text = variants[variant_index]
    await state.update_data(selected_variant=variant_index, text=selected_text)
    
    text = (
        f"✅ <b>Выбран вариант {variant_index + 1}</b>\n\n"
        "<b>Текст кампании:</b>\n"
        f"<code>{selected_text[:500]}{'...' if len(selected_text) > 500 else ''}</code>\n\n"
        "Что хотите сделать дальше?"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_campaign_editor_keyboard(selected_text),
    )


# ──────────────────────────────────────────────────────────────
# Редактирование текста
# ──────────────────────────────────────────────────────────────

@router.callback_query(AIEditCB.filter(F.action == "edit_text"))
async def edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактирование текста кампании."""
    await state.set_state(CampaignCreateState.editing_text)
    
    data = await state.get_data()
    current_text = data.get("text", "")
    
    text = (
        "✏️ <b>Редактирование текста</b>\n\n"
        "<b>Текущий текст:</b>\n"
        f"<code>{current_text}</code>\n\n"
        "👇 <b>Напишите новый текст ниже</b> или отправьте изменения:\n\n"
        "<i>Можете отредактировать весь текст или только часть.</i>\n"
        "<i>Для отмены отправьте: /cancel</i>"
    )
    
    await callback.message.edit_text(text)


@router.message(CampaignCreateState.editing_text)
async def process_text_edit(message: Message, state: FSMContext) -> None:
    """Получили отредактированный текст."""
    new_text = message.text
    await state.update_data(text=new_text)
    
    data = await state.get_data()
    has_url = bool(data.get("url"))
    has_image = bool(data.get("image_file_id"))
    
    await message.answer(
        "✅ Текст обновлен!\n\n"
        "Что хотите сделать дальше?",
        reply_markup=get_campaign_editor_keyboard(new_text, has_url, has_image),
    )
    await state.set_state(CampaignCreateState.selecting_variant)


# ──────────────────────────────────────────────────────────────
# Добавление URL
# ──────────────────────────────────────────────────────────────

@router.callback_query(AIEditCB.filter(F.action == "add_url"))
async def add_url(callback: CallbackQuery, state: FSMContext) -> None:
    """Добавление URL кампании."""
    await state.set_state(CampaignCreateState.waiting_for_url)
    
    data = await state.get_data()
    current_url = data.get("url", "")
    
    text = (
        "🔗 <b>Добавление ссылки</b>\n\n"
        f"<b>Текущая ссылка:</b> {current_url if current_url else 'не добавлена'}\n\n"
        "👇 <b>Отправьте URL</b>, куда будут переходить пользователи:\n\n"
        "<i>Пример:</i>\n"
        "<i>https://t.me/your_channel</i>\n"
        "<i>https://yoursite.com/landing</i>\n\n"
        "<i>Для пропуска отправьте: /skip</i>\n"
        "<i>Для отмены: /cancel</i>"
    )
    
    await callback.message.edit_text(text)


@router.message(CampaignCreateState.waiting_for_url)
async def process_url(message: Message, state: FSMContext) -> None:
    """Получили URL."""
    url = message.text
    
    # Простая валидация URL
    if not url.startswith(("http://", "https://", "t.me/")):
        await message.answer(
            "❌ Неверный формат URL.\n\n"
            "URL должен начинаться с:\n"
            "• http://\n"
            "• https://\n"
            "• t.me/\n\n"
            "Попробуйте еще раз:"
        )
        return
    
    await state.update_data(url=url)
    
    data = await state.get_data()
    current_text = data.get("text", "")
    has_image = bool(data.get("image_file_id"))
    
    await message.answer(
        f"✅ URL добавлен: {url}\n\n"
        "Что хотите сделать дальше?",
        reply_markup=get_campaign_editor_keyboard(current_text, has_url=True, has_image=has_image),
    )
    await state.set_state(CampaignCreateState.selecting_variant)


# ──────────────────────────────────────────────────────────────
# Добавление изображения
# ──────────────────────────────────────────────────────────────

@router.callback_query(AIEditCB.filter(F.action == "add_image"))
async def add_image(callback: CallbackQuery, state: FSMContext) -> None:
    """Добавление изображения."""
    await state.set_state(CampaignCreateState.waiting_for_image)
    
    text = (
        "🖼️ <b>Добавление изображения</b>\n\n"
        "👇 <b>Отправьте изображение</b> для кампании:\n\n"
        "<i>Можно отправить фото или файл.</i>\n"
        "<i>Для пропуска отправьте: /skip</i>\n"
        "<i>Для отмены: /cancel</i>"
    )
    
    await callback.message.edit_text(text)


@router.message(CampaignCreateState.waiting_for_image, F.photo)
async def process_image_photo(message: Message, state: FSMContext) -> None:
    """Получили изображение (фото)."""
    # Берем фото наилучшего качества
    image_file_id = message.photo[-1].file_id
    await state.update_data(image_file_id=image_file_id)
    
    data = await state.get_data()
    current_text = data.get("text", "")
    has_url = bool(data.get("url"))
    
    await message.answer(
        "✅ Изображение добавлено!\n\n"
        "Что хотите сделать дальше?",
        reply_markup=get_campaign_editor_keyboard(current_text, has_url, has_image=True),
    )
    await state.set_state(CampaignCreateState.selecting_variant)


@router.message(CampaignCreateState.waiting_for_image, F.document)
async def process_image_document(message: Message, state: FSMContext) -> None:
    """Получили изображение (файл)."""
    # Проверяем, что это изображение
    if message.document.mime_type.startswith("image/"):
        image_file_id = message.document.file_id
        await state.update_data(image_file_id=image_file_id)
        
        data = await state.get_data()
        current_text = data.get("text", "")
        has_url = bool(data.get("url"))
        
        await message.answer(
            "✅ Изображение добавлено!\n\n"
            "Что хотите сделать дальше?",
            reply_markup=get_campaign_editor_keyboard(current_text, has_url, has_image=True),
        )
        await state.set_state(CampaignCreateState.selecting_variant)
    else:
        await message.answer(
            "❌ Это не изображение. Отправьте файл с изображением или /skip для пропуска."
        )


# ──────────────────────────────────────────────────────────────
# Подтверждение и создание
# ──────────────────────────────────────────────────────────────

@router.callback_query(AIEditCB.filter(F.action == "confirm"))
async def confirm_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение и создание кампании."""
    data = await state.get_data()
    
    text = data.get("text", "")
    url = data.get("url")
    image_file_id = data.get("image_file_id")
    topic = data.get("topic", "default")
    description = data.get("description", "")
    
    # Формируем превью кампании
    preview = (
        "📋 <b>Предпросмотр кампании</b>\n\n"
        f"<b>Тематика:</b> {topic}\n"
        f"<b>Текст:</b> {len(text)} символов\n"
        f"<b>Ссылка:</b> {url if url else 'не добавлена'}\n"
        f"<b>Изображение:</b> {'✅' if image_file_id else '❌'}\n\n"
        f"<b>Описание:</b>\n<i>{description}</i>\n\n"
        "Готовы создать кампанию?"
    )
    
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Создать кампанию", callback_data="campaign_confirm_create")],
            [InlineKeyboardButton(text="✏️ Назад к редактированию", callback_data=AIEditCB(action="edit_text").pack())],
        ]
    )
    
    if image_file_id:
        await callback.message.answer_photo(
            photo=image_file_id,
            caption=preview,
            reply_markup=keyboard,
        )
    else:
        await callback.message.answer(
            preview,
            reply_markup=keyboard,
        )


@router.callback_query(F.data == "campaign_confirm_create")
async def final_create_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """Финальное создание кампании."""
    data = await state.get_data()
    
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        campaign_repo = CampaignRepository(session)
        
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        text = data.get("text", "")
        url = data.get("url")
        image_file_id = data.get("image_file_id")
        topic = data.get("topic", "default")
        description = data.get("description", "")
        
        # Создаем кампанию
        campaign = await campaign_repo.create({
            "user_id": user.id,
            "title": f"AI кампания: {topic}",
            "text": text,
            "topic": topic,
            "header": url,  # Используем header для URL
            "image_file_id": image_file_id,
            "status": "draft",
            "filters_json": {},
        })
        
        await state.clear()
        
        success_text = (
            f"✅ <b>Кампания создана!</b>\n\n"
            f"<b>ID:</b> {campaign.id}\n"
            f"<b>Текст:</b> {len(text)} символов\n"
            f"<b>Статус:</b> Черновик\n\n"
            "Теперь вы можете:\n"
            "• Запустить кампанию из раздела «Мои кампании»\n"
            "• Отредактировать настройки\n"
            "• Выбрать чаты для рассылки"
        )
        
        from src.bot.keyboards.main_menu import MainMenuCB
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Мои кампании", callback_data=MainMenuCB(action="my_campaigns").pack())],
                [InlineKeyboardButton(text="🏠 В меню", callback_data=MainMenuCB(action="main_menu").pack())],
            ]
        )
        
        await callback.message.answer(success_text, reply_markup=keyboard)


# ──────────────────────────────────────────────────────────────
# Отмена
# ──────────────────────────────────────────────────────────────

@router.message(F.text == "/cancel")
async def cancel_create(message: Message, state: FSMContext) -> None:
    """Отмена создания кампании."""
    await state.clear()
    await message.answer("❌ Создание кампании отменено.")


@router.message(F.text == "/skip")
async def skip_step(message: Message, state: FSMContext) -> None:
    """Пропуск шага."""
    current_state = await state.get_state()
    
    if current_state == CampaignCreateState.waiting_for_url:
        await message.answer("⏭️ URL пропущен.")
        await state.set_state(CampaignCreateState.selecting_variant)
    elif current_state == CampaignCreateState.waiting_for_image:
        await message.answer("⏭️ Изображение пропущено.")
        await state.set_state(CampaignCreateState.selecting_variant)
