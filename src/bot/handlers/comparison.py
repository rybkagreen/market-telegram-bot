"""Handler'ы для сравнения каналов."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.bot.keyboards.comparison import (
    ComparisonCB,
    get_channel_with_compare_kb,
    get_comparison_result_kb,
)
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(ComparisonCB.filter(F.action == "toggle"))
async def toggle_channel_for_comparison(
    callback: CallbackQuery,
    callback_data: ComparisonCB,
    state: FSMContext,
) -> None:
    """Добавить/убрать канал из сравнения."""
    channel_id = int(callback_data.channel_id)

    # Получить текущие выбранные каналы
    data = await state.get_data()
    selected = data.get("comparison_selected_channels", [])

    # Toggle
    if channel_id in selected:
        selected.remove(channel_id)
        await callback.answer("❌ Убран из сравнения", show_alert=False)
    else:
        # Максимум 5 каналов для сравнения
        if len(selected) >= 5:
            await callback.answer(
                "❌ Можно сравнивать максимум 5 каналов",
                show_alert=True,
            )
            return
        selected.append(channel_id)
        await callback.answer("✅ Добавлен в сравнение", show_alert=False)

    await state.update_data(comparison_selected_channels=selected)

    # Перерисовать кнопку
    # Для этого нужно получить данные канала
    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat

        channel = await session.get(TelegramChat, channel_id)
        if channel:
            is_selected = channel_id in selected
            keyboard = get_channel_with_compare_kb(
                channel_id=channel_id,
                channel_username=channel.username or "",
                is_selected=is_selected,
            )

            # Обновить кнопку если возможно
            try:
                if callback.message and hasattr(callback.message, "edit_reply_markup"):
                    await callback.message.edit_reply_markup(reply_markup=keyboard)  # type: ignore
            except Exception as e:
                logger.debug(f"Failed to update reply markup: {e}")


@router.callback_query(ComparisonCB.filter(F.action == "compare"))
async def show_comparison(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать сравнение выбранных каналов."""
    data = await state.get_data()
    selected = data.get("comparison_selected_channels", [])

    if len(selected) < 2:
        await callback.answer(
            "❌ Выберите минимум 2 канала для сравнения",
            show_alert=True,
        )
        return

    # Получить данные каналов
    from src.core.services.comparison_service import comparison_service

    channels_data = await comparison_service.get_channels_for_comparison(selected)
    comparison = comparison_service.calculate_comparison_metrics(channels_data)

    # Сформировать текст сравнения
    text = "📊 <b>Сравнение каналов</b>\n\n"
    text += "<b>━━━ ТАБЛИЦА ━━━</b>\n\n"

    # Заголовок таблицы
    headers = ["Метрика"]
    for ch in comparison["channels"]:
        name = ch.get("title") or ch.get("username") or f"Канал {ch['id']}"
        headers.append(name[:15])

    text += " | ".join(headers) + "\n"
    text += " | ".join(["─" * 15] * len(headers)) + "\n"

    # Строки метрик
    metrics = [
        ("👥 Подписчики", "member_count", lambda x: f"{x:,}"),  # type: ignore[no-untyped-call]  # lambda type inference
        ("👁 Просмотры", "avg_views", lambda x: f"{x:,}"),  # type: ignore[no-untyped-call]  # lambda type inference
        ("📈 ER", "er", lambda x: f"{x:.1f}%"),  # type: ignore[no-untyped-call]  # lambda type inference
        ("📝 Постов/день", "post_frequency", lambda x: f"{x:.1f}"),  # type: ignore[no-untyped-call]  # lambda type inference
        ("💰 Цена", "price_per_post", lambda x: f"{x:.0f} кр"),  # type: ignore[no-untyped-call]  # lambda type inference
        ("💰 Цена/1К подп", "price_per_1k_subscribers", lambda x: f"{x:.0f} кр"),  # type: ignore[no-untyped-call]  # lambda type inference
    ]

    for label, metric, formatter in metrics:
        row = [label]
        for ch in comparison["channels"]:
            value = ch.get(metric, 0)
            formatted = formatter(value)  # type: ignore[no-untyped-call]  # lambda formatter
            # Пометить лучшее значение
            if ch.get("is_best", {}).get(metric):
                formatted = f"✅ {formatted}"
            row.append(formatted)
        text += " | ".join(row) + "\n"

    # Рекомендация
    rec = comparison.get("recommendation", {})
    if rec.get("channel_id"):
        text += f"\n🏆 <b>Рекомендация:</b> {rec.get('channel_name')}\n"
        text += f"   {rec.get('reason')}\n"

    keyboard = get_comparison_result_kb(selected)

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(ComparisonCB.filter(F.action == "clear"))
async def clear_comparison(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Сбросить выбранные каналы."""
    await state.update_data(comparison_selected_channels=[])
    await callback.answer("✅ Сравнение сброшено", show_alert=False)

    # Вернуться к каталогу
    from src.bot.handlers.channels_db import handle_categories

    await handle_categories(callback)


@router.callback_query(ComparisonCB.filter(F.action == "show_bar"))
async def show_comparison_bar(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать панель сравнения."""
    data = await state.get_data()
    selected = data.get("comparison_selected_channels", [])

    text = (
        f"📊 <b>Сравнение каналов</b>\n\n"
        f"Выбрано каналов: <b>{len(selected)}</b>\n\n"
        f"Минимум 2, максимум 5 каналов для сравнения.\n\n"
    )

    if selected:
        text += "<b>Выбранные каналы:</b>\n"
        async with async_session_factory() as session:
            from src.db.models.analytics import TelegramChat

            for channel_id in selected:
                channel = await session.get(TelegramChat, channel_id)
                if channel:
                    name = channel.title or channel.username or f"Канал {channel_id}"
                    text += f"• {name}\n"

    # Создать новую клавиатуру с дополнительной кнопкой
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from src.bot.keyboards.channels import ChannelsCB

    builder = InlineKeyboardBuilder()

    # Копировать существующие кнопки
    if selected:
        builder.button(
            text=f"📊 Сравнить ({len(selected)})",
            callback_data=ComparisonCB(action="compare").pack(),
        )
        builder.button(
            text="❌ Сбросить",
            callback_data=ComparisonCB(action="clear").pack(),
        )
        builder.adjust(2)
    else:
        builder.button(
            text="📋 Выбрать каналы",
            callback_data=ChannelsCB(action="show_compare_list", value="all").pack(),
        )
        builder.button(
            text="🔙 В каталог",
            callback_data=ChannelsCB(action="categories").pack(),
        )
        builder.adjust(1, 1)

    # Добавить кнопку "Изменить выбор" если есть выбранные
    if selected:
        builder.button(
            text="📋 Изменить выбор",
            callback_data=ChannelsCB(action="show_compare_list", value="all").pack(),
        )
        builder.adjust(1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup(), parse_mode="HTML")
