"""
Admin AI Handlers — ИИ-генерация кампаний.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.filters.admin import AdminFilter
from src.bot.keyboards.admin import AdminCB, get_back_kb
from src.bot.states.admin import AdminAIGenerateStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.core.services.ai_service import admin_ai_service

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


# ==================== ИИ-ГЕНЕРАЦИЯ КАМПАНИИ ====================


@router.callback_query(AdminCB.filter(F.action == "ai_generate"))
async def handle_ai_generate_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать ИИ-генерацию кампании."""
    await state.clear()
    await state.set_state(AdminAIGenerateStates.waiting_description)

    await safe_callback_edit(callback, "🤖 <b>ИИ-генерация кампании</b>\n\n"
        "Опишите, о чём должна быть рекламная кампания.\n"
        "ИИ сгенерирует название, текст и варианты A/B тестирования.\n\n"
        "Пример: 'Продвижение онлайн-курса по программированию для начинающих'\n\n"
        "Введите описание:", reply_markup=get_back_kb())
    await callback.answer()


@router.message(AdminAIGenerateStates.waiting_description)
async def handle_ai_generate_description(message: Message, state: FSMContext) -> None:
    """Обработать описание для ИИ-генерации."""
    if not message.text:
        await message.answer("Пожалуйста, введите текст.")
        return
    description = message.text.strip()

    if len(description) < 10 or len(description) > 500:
        await message.answer("❌ Описание должно быть от 10 до 500 символов.")
        return

    await state.update_data(ai_description=description)
    await message.answer("⏳ Генерирую кампанию через ИИ...")

    try:
        # Генерируем A/B варианты (админ = ADMIN тариф с бесплатной моделью)
        variants = await admin_ai_service.generate_ab_variants(
            description=description,
            user_plan="admin",
            count=3,
        )

        # Сохраняем варианты
        await state.update_data(ai_variants=variants)

        # Формируем текст с вариантами
        text = "✅ <b>ИИ сгенерировал 3 варианта</b>\n\nВыберите лучший:\n\n"
        for i, variant in enumerate(variants, 1):
            text += f"<b>Вариант {i}:</b>\n{variant}\n\n"

        builder = InlineKeyboardBuilder()
        for i in range(1, 4):
            builder.button(text=f"Вариант {i}", callback_data=AdminCB(action="ai_variant_select", value=str(i)))
        builder.button(text="🔄 Перегенерировать", callback_data=AdminCB(action="ai_regenerate"))
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
        builder.adjust(1, 1, 1)

        await message.answer(text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"AI generation error: {e}")
        await message.answer(
            "❌ Ошибка при генерации через ИИ.\n"
            f"Попробуйте ещё раз или введите текст вручную.\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=get_back_kb()
        )
        await state.set_state(AdminAIGenerateStates.waiting_description)


@router.callback_query(AdminCB.filter(F.action == "ai_regenerate"))
async def handle_ai_regenerate(callback: CallbackQuery, state: FSMContext) -> None:
    """Перегенерировать варианты через ИИ."""
    data = await state.get_data()
    description = data.get("ai_description", "")

    await safe_callback_edit(callback, "⏳ Перегенерирую варианты...")

    try:
        variants = await admin_ai_service.generate_ab_variants(
            description=description,
            user_plan="admin",
            count=3,
        )
        await state.update_data(ai_variants=variants)

        text = "✅ <b>ИИ сгенерировал 3 варианта</b>\n\nВыберите лучший:\n\n"
        for i, variant in enumerate(variants, 1):
            text += f"<b>Вариант {i}:</b>\n{variant}\n\n"

        builder = InlineKeyboardBuilder()
        for i in range(1, 4):
            builder.button(text=f"Вариант {i}", callback_data=AdminCB(action="ai_variant_select", value=str(i)))
        builder.button(text="🔄 Перегенерировать", callback_data=AdminCB(action="ai_regenerate"))
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
        builder.adjust(1, 1, 1)

        await safe_callback_edit(callback, text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"AI regeneration error: {e}")
        await safe_callback_edit(callback, "❌ Ошибка при перегенерации.\nПопробуйте ещё раз.", reply_markup=get_back_kb())


@router.callback_query(AdminCB.filter(F.action == "ai_variant_select"))
async def handle_ai_variant_select(callback: CallbackQuery, callback_data: AdminCB, state: FSMContext) -> None:
    """Выбрать вариант кампании."""
    from src.bot.keyboards.campaign import get_topics_kb

    variant_index = int(callback_data.value) - 1
    data = await state.get_data()
    variants = data.get("ai_variants", [])

    if not variants or variant_index >= len(variants):
        await callback.answer("❌ Вариант не найден", show_alert=True)
        return

    selected_text = variants[variant_index]
    await state.update_data(text=selected_text, selected_variant=variant_index + 1)

    # Генерируем название на основе описания (бесплатно для админа)
    await safe_callback_edit(callback, "⏳ Генерирую название...")

    try:
        title = await admin_ai_service.generate(
            prompt=f"Придумай короткое название (2-4 слова) для рекламной кампании: {data.get('ai_description', '')}",
            system="Ты профессиональный маркетолог. Придумай короткое и запоминающееся название для рекламной кампании.",
        )
        title = title.strip()[:100]
        await state.update_data(title=title)

        await state.set_state(AdminAIGenerateStates.waiting_topic)
        await safe_callback_edit(callback, f"✅ <b>Кампания сгенерирована!</b>\n\n"
            f"📋 <b>Название:</b> {title}\n"
            f"📝 <b>Текст:</b> {selected_text[:200]}...\n\n"
            f"Выберите тематику для рассылки:", reply_markup=get_topics_kb())

    except Exception as e:
        logger.error(f"AI title generation error: {e}")
        title = f"Кампания #{variant_index + 1}"
        await state.update_data(title=title)
        await state.set_state(AdminAIGenerateStates.waiting_topic)
        await safe_callback_edit(callback, f"✅ <b>Кампания сгенерирована!</b>\n\n"
            f"📋 <b>Название:</b> {title}\n"
            f"📝 <b>Текст:</b> {selected_text[:200]}...\n\n"
            f"Выберите тематику для рассылки:", reply_markup=get_topics_kb())
