"""Advertiser campaigns handler."""

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.advertiser.my_campaigns import my_campaigns_kb
from src.bot.keyboards.advertiser.placement import (
    camp_confirm_kb,
    video_confirm_keyboard,
    video_upload_keyboard,
)
from src.bot.states.placement import PlacementStates
from src.bot.utils.safe_callback import safe_callback_edit

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(lambda c: c.data == "main:my_campaigns")
async def show_my_campaigns(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать мои кампании."""
    from src.db.repositories.placement_request_repo import PlacementRequestRepository
    from src.db.repositories.user_repo import UserRepository

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    campaigns: list[dict] = []
    if user:
        placements = await PlacementRequestRepository(session).get_by_advertiser(user.id)
        campaigns = [
            {
                "id": p.id,
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            }
            for p in placements
        ]
    text = "📋 Мои кампании"
    await safe_callback_edit(callback, text, reply_markup=my_campaigns_kb(campaigns))


@router.callback_query(lambda c: c.data.startswith("camp:detail:"))
async def camp_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    """Детали кампании."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from src.bot.utils.safe_callback import safe_callback_edit
    from src.db.models.placement_request import PlacementRequest, PlacementStatus
    from src.db.models.telegram_chat import TelegramChat
    from src.db.repositories.user_repo import UserRepository

    placement_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, placement_id)
    if not req:
        await callback.answer("❌ Кампания не найдена", show_alert=True)
        return

    # Verify ownership
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user or req.advertiser_id != user.id:
        await callback.answer("❌ У вас нет доступа к этой кампании", show_alert=True)
        return

    # Fetch channel info
    channel = await session.get(TelegramChat, req.channel_id)
    channel_name = (
        f"@{channel.username}" if channel and channel.username else f"ID: {req.channel_id}"
    )

    # Format status
    status_labels: dict[str, str] = {
        "pending_owner": "⏳ Ожидает ответа владельца",
        "counter_offer": "💬 Контр-предложение",
        "pending_payment": "💳 Ожидает оплаты",
        "escrow": "🔒 В эскроу",
        "published": "✅ Опубликовано",
        "failed": "❌ Ошибка публикации",
        "failed_permissions": "❌ Нет прав у бота",
        "refunded": "💰 Возвращено",
        "cancelled": "🚫 Отменено",
    }
    status_label = status_labels.get(req.status, req.status)

    # Format price
    price = req.final_price or req.proposed_price or 0
    price_str = f"{price:.0f} ₽"

    # Format schedule
    schedule = req.final_schedule or req.proposed_schedule
    schedule_str = schedule.strftime("%d.%m.%Y %H:%M") if schedule else "По договорённости"

    # Format format type
    format_labels_map: dict[str, str] = {
        "post_24h": "Пост 24ч",
        "post_48h": "Пост 48ч",
        "post_7d": "Пост 7 дней",
        "pin_24h": "Закреп 24ч",
        "pin_48h": "Закреп 48ч",
    }
    fmt_label = format_labels_map.get(
        req.publication_format or "post_24h", req.publication_format or "—"
    )

    # Ad text preview
    ad_text_preview = ""
    if req.ad_text:
        ad_text_preview = (req.ad_text[:200] + "...") if len(req.ad_text) > 200 else req.ad_text

    # Build detail text
    text = (
        f"📋 *Кампания #{req.id}*\n\n"
        f"📺 Канал: {channel_name}\n"
        f"📊 Статус: {status_label}\n"
        f"💰 Цена: {price_str}\n"
        f"📝 Формат: {fmt_label}\n"
        f"📅 Публикация: {schedule_str}\n"
    )

    if req.published_at:
        text += f"✅ Опубликована: {req.published_at.strftime('%d.%m.%Y %H:%M')}\n"
    if req.deleted_at:
        text += f"🗑 Удалена: {req.deleted_at.strftime('%d.%m.%Y %H:%M')}\n"
    if req.rejection_reason and req.status in (
        PlacementStatus.failed,
        PlacementStatus.cancelled,
    ):
        text += f"📝 Причина: {req.rejection_reason}\n"

    if ad_text_preview:
        text += f"\n📄 Текст:\n_{ad_text_preview}_"

    # Build action buttons based on status
    builder = InlineKeyboardBuilder()

    if req.status == PlacementStatus.pending_payment:
        builder.button(text="💳 Оплатить", callback_data=f"camp:pay:balance:{req.id}")
        builder.button(text="❌ Отменить", callback_data=f"camp:cancel:{req.id}")
    elif req.status == PlacementStatus.escrow:
        builder.button(text="📋 Отслеживать статус", callback_data=f"camp:status:{req.id}")
        builder.button(
            text="❌ Отменить (возврат 50%)", callback_data=f"camp:cancel_after_escrow:{req.id}"
        )
    elif req.status == PlacementStatus.published:
        builder.button(text="📋 Статус публикации", callback_data=f"camp:status:{req.id}")
    elif req.status == PlacementStatus.counter_offer:
        builder.button(text="✅ Принять", callback_data=f"camp:counter:accept:{req.id}")
        builder.button(text="✏️ Контр-предложение", callback_data=f"camp:counter:reply:{req.id}")
    elif req.status == PlacementStatus.pending_owner:
        builder.button(text="⏳ Ожидает ответа владельца", callback_data="main:my_campaigns")
    # Terminal states (cancelled, refunded, failed) — view only, no action buttons

    builder.button(text="📋 Все кампании", callback_data="main:my_campaigns")
    builder.adjust(1)

    await safe_callback_edit(
        callback, text, reply_markup=builder.as_markup(), parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data.startswith("camp:cancel:"))
async def camp_cancel(callback: CallbackQuery) -> None:
    """Отменить кампанию."""
    await callback.answer("Кампания отменена", show_alert=True)


# ISSUE #11: Принять контр-предложение
@router.callback_query(F.data.startswith("camp:counter:accept:"))
async def camp_counter_accept(callback: CallbackQuery, session: AsyncSession) -> None:
    """Рекламодатель принимает контр-предложение владельца."""
    from src.db.models.placement_request import PlacementRequest, PlacementStatus

    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req or req.status != PlacementStatus.counter_offer:
        await callback.answer("❌ Контр-предложение недоступно", show_alert=True)
        return

    if req.counter_price:
        req.final_price = req.counter_price
    if req.counter_schedule:
        req.final_schedule = req.counter_schedule
    req.status = PlacementStatus.pending_payment

    from datetime import UTC, datetime, timedelta

    req.expires_at = datetime.now(UTC) + timedelta(hours=24)
    await session.commit()

    price = req.final_price or req.proposed_price
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить {price:.0f} ₽", callback_data=f"camp:pay:{request_id}")
    builder.button(text="❌ Отменить", callback_data=f"camp:cancel:{request_id}")
    builder.adjust(1)

    schedule_str = req.final_schedule.strftime("%d.%m.%Y %H:%M") if req.final_schedule else "—"
    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        f"✅ *Условия приняты!*\n\n"
        f"💰 Итоговая цена: *{price:.0f} ₽*\n"
        f"📅 Время публикации: *{schedule_str}*\n\n"
        f"⏱ Оплатите в течение 24 часов.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ISSUE #11: Начать раунд контр-переговоров
@router.callback_query(F.data.startswith("camp:counter:reply:"))
async def camp_counter_reply(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Рекламодатель отправляет встречное предложение по цене."""
    from src.db.models.placement_request import PlacementRequest

    request_id = int((callback.data or "").split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if req.counter_offer_count >= 3:
        await callback.answer("❌ Достигнут лимит раундов (3/3)", show_alert=True)
        return

    await state.update_data(counter_request_id=request_id)
    await state.set_state(PlacementStates.arbitrating)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=f"camp:cancel:{request_id}")

    price = req.counter_price or req.proposed_price
    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        f"✏️ *Контр-предложение*\n\n"
        f"Раунд: *{req.counter_offer_count + 1}/3*\n"
        f"Текущая цена: *{price:.0f} ₽*\n\n"
        f"Введите вашу цену (число в рублях):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ISSUE #11: Обработка ввода цены контр-предложения
@router.message(PlacementStates.arbitrating)
async def camp_counter_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Принять цену контр-предложения от рекламодателя."""
    from src.db.models.placement_request import PlacementRequest, PlacementStatus

    data = await state.get_data()
    request_id = data.get("counter_request_id")

    if not request_id:
        await state.clear()
        return

    try:
        new_price = Decimal((message.text or "").strip().replace(" ", ""))
        if new_price < Decimal("100"):
            await message.answer("❌ Минимальная цена 100 ₽")
            return
    except Exception:
        await message.answer("❌ Введите число (например: 450)")
        return

    req = await session.get(PlacementRequest, request_id)
    if not req:
        await state.clear()
        return

    # FIX #6: Use advertiser_counter_price to prevent data collision with owner's counter
    req.advertiser_counter_price = new_price
    req.counter_offer_count += 1
    req.status = PlacementStatus.pending_owner

    from datetime import UTC, datetime, timedelta

    req.expires_at = datetime.now(UTC) + timedelta(hours=24)
    await session.commit()
    await state.clear()

    # Уведомить владельца канала
    from src.bot.handlers.shared.notifications import notify_placement_new
    from src.db.models.user import User

    owner = await session.get(User, req.owner_id)
    if owner and message.bot:
        try:
            notify_kb = InlineKeyboardBuilder()
            # FIX #3: Use correct callback pattern (own:request:)
            notify_kb.button(text="👀 Посмотреть", callback_data=f"own:request:{request_id}")
            await notify_placement_new(
                message.bot, owner.telegram_id, request_id, notify_kb.as_markup()
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to owner: {e}")

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои кампании", callback_data="main:my_campaigns")

    await message.answer(
        f"✅ *Контр-предложение отправлено!*\n\n"
        f"💰 Ваша цена: *{new_price:.0f} ₽*\n"
        f"⏱ Владелец должен ответить в течение 24 часов.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


# ── Video upload flow (S3 addition) ──────────────────────────────────────────


async def _proceed_after_video(
    event: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:  # noqa: ARG001
    """Перейти к подтверждению кампании после (необязательного) шага с видео."""
    await state.set_state(PlacementStates.waiting_response)
    if not isinstance(event.message, Message):
        return
    await event.message.answer("✅ Подтвердите кампанию:", reply_markup=camp_confirm_kb())


@router.callback_query(F.data == "campaign:skip_video")
async def camp_skip_video(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Пропустить добавление видео."""
    await state.update_data(media_type="none")
    await _proceed_after_video(callback, state, session)
    await callback.answer()


@router.callback_query(F.data == "campaign:add_video")
async def camp_add_video(callback: CallbackQuery, state: FSMContext) -> None:
    """Перейти к загрузке видео."""
    await state.set_state(PlacementStates.upload_video)
    if isinstance(callback.message, Message):
        await callback.message.answer("Отправьте видеофайл (до 2 минут, до 50 МБ):")
    await callback.answer()


@router.callback_query(F.data == "campaign:video_confirm")
async def camp_video_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Подтвердить загруженное видео и продолжить."""
    await _proceed_after_video(callback, state, session)
    await callback.answer()


@router.callback_query(F.data == "campaign:remove_video")
async def camp_remove_video(callback: CallbackQuery, state: FSMContext) -> None:
    """Удалить видео и предложить загрузить другое."""
    await state.update_data(
        media_type="none", video_file_id=None, video_duration=None, video_thumbnail_file_id=None
    )
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "Видео удалено. Хотите добавить другое?", reply_markup=video_upload_keyboard()
        )
    await callback.answer()


@router.message(PlacementStates.upload_video)
async def camp_upload_video(message: Message, state: FSMContext) -> None:
    """Принять видеофайл с валидацией длительности и размера."""
    if not message.video:
        await message.answer("Пожалуйста, отправьте видеофайл (не фото, не документ).")
        return
    _max_duration = 120
    _max_size = 50 * 1024 * 1024
    if message.video.duration and message.video.duration > _max_duration:
        await message.answer(
            f"❌ Видео слишком длинное. Максимум {_max_duration} секунд (2 минуты)."
        )
        return
    if message.video.file_size and message.video.file_size > _max_size:
        await message.answer("❌ Файл слишком большой. Максимум 50 МБ.")
        return
    thumbnail_file_id = message.video.thumbnail.file_id if message.video.thumbnail else None
    await state.update_data(
        media_type="video",
        video_file_id=message.video.file_id,
        video_duration=message.video.duration,
        video_thumbnail_file_id=thumbnail_file_id,
    )

    # --- Store video result for Mini App polling (S7 addition) ---
    fsm_data = await state.get_data()
    _session_id = fsm_data.get("video_upload_session_id")
    if _session_id:
        import json as _json

        import redis.asyncio as aioredis

        from src.config.settings import settings as _settings

        _r = aioredis.from_url(str(_settings.redis_url))
        _video_data = _json.dumps({
            "file_id": message.video.file_id,
            "duration": message.video.duration,
            "thumbnail_file_id": thumbnail_file_id,
        })
        await _r.setex(f"video_result:{_session_id}", 300, _video_data)
        await _r.delete(f"pending_video:{_session_id}")
        await _r.close()
        await message.answer("✅ Видео получено. Вернитесь в приложение.")
        return
    # --- end video result storage ---

    duration_str = f"{message.video.duration}с" if message.video.duration else "—"
    await message.answer(
        f"✅ Видео загружено ({duration_str})", reply_markup=video_confirm_keyboard()
    )
