"""Dispute handler — full dispute flow."""

import contextlib
import logging
import re
from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.shared.notifications import (
    notify_admin_new_dispute,
    notify_dispute_opened_owner,
)
from src.bot.states.dispute import DisputeStates
from src.db.models.dispute import DisputeReason, DisputeStatus, PlacementDispute
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.repositories.dispute_repo import DisputeRepository
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = Router()

_REASON_LABELS = {
    "post_removed_early": "Пост удалён раньше срока",
    "bot_kicked": "Бот удалён из канала",
    "advertiser_complaint": "Жалоба рекламодателя",
}

_STATUS_LABELS = {
    "open": "🔴 Открыт — ожидает объяснения владельца",
    "owner_explained": "🟡 Владелец объяснил — ждёт решения администратора",
    "resolved": "🟢 Разрешён",
}

_FORMAT_HOURS = {
    "post_24h": 24,
    "post_48h": 48,
    "post_7d": 168,
    "pin_24h": 24,
    "pin_48h": 48,
}


def _compute_actual_hours(req: PlacementRequest) -> int:
    """Return how many hours the post actually stayed live (0 if not determinable)."""
    if req.published_at and req.deleted_at:
        delta = req.deleted_at - req.published_at
        return int(delta.total_seconds() / 3600)
    return 0


# ---------------------------------------------------------------------------
# dispute:open:{placement_id}
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^dispute:open:(\d+)$"))
async def open_dispute(callback: CallbackQuery, session: AsyncSession) -> None:
    """Открыть спор по размещению."""
    placement_id = int((callback.data or "").split(":")[-1])

    req = await session.get(PlacementRequest, placement_id)
    if not req:
        await callback.answer("❌ Размещение не найдено", show_alert=True)
        return

    if req.status != PlacementStatus.published:
        await callback.answer("❌ Спор можно открыть только по активной публикации", show_alert=True)
        return

    # Проверить — нет ли уже открытого спора
    existing = await DisputeRepository(session).get_by_placement(placement_id)
    if existing:
        callback.data = f"dispute:detail:{existing.id}"
        await show_dispute_detail(callback, session)
        return

    channel = await session.get(TelegramChat, req.channel_id)

    # Определить причину автоматически
    reason = DisputeReason.advertiser_complaint
    if req.deleted_at and req.scheduled_delete_at and req.deleted_at < req.scheduled_delete_at - timedelta(minutes=5):
        reason = DisputeReason.post_removed_early

    price = req.final_price if req.final_price is not None else req.proposed_price

    dispute = PlacementDispute(
        placement_request_id=placement_id,
        advertiser_id=req.advertiser_id,
        owner_id=req.owner_id,
        reason=reason,
        status=DisputeStatus.open,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(dispute)
    await session.commit()
    await session.refresh(dispute)

    reason_human = _REASON_LABELS.get(reason.value, reason.value)

    # Вычислить продолжительность
    fmt_val = req.publication_format.value if hasattr(req.publication_format, "value") else str(req.publication_format)
    paid_h = _FORMAT_HOURS.get(fmt_val, 24)
    actual_h = _compute_actual_hours(req)

    # Уведомить владельца
    owner = await session.get(User, req.owner_id)
    if owner and callback.bot:
        try:
            await notify_dispute_opened_owner(
                bot=callback.bot,
                owner_telegram_id=owner.telegram_id,
                dispute_id=dispute.id,
            )
        except Exception as exc:
            logger.warning("notify owner dispute failed: %s", exc)

    # Уведомить всех админов
    admins_result = await session.execute(select(User).where(User.is_admin == True))  # noqa: E712
    if callback.bot:
        for admin in admins_result.scalars().all():
            with contextlib.suppress(Exception):
                await notify_admin_new_dispute(
                    bot=callback.bot,
                    admin_telegram_id=admin.telegram_id,
                    dispute_id=dispute.id,
                    placement_id=placement_id,
                )

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Детали спора", callback_data=f"dispute:detail:{dispute.id}")
    builder.button(text="💬 Написать администратору", callback_data="main:feedback")
    builder.adjust(1)

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        f"⚠️ *Открыт спор по заявке #{placement_id}*\n\n"
        f"📺 Канал: @{channel.username if channel else '—'}\n"
        f"💰 Сумма в эскроу: *{price:.0f} ₽*\n\n"
        f"🔍 Причина: *{reason_human}*\n"
        f"⏱ Прожило: {actual_h} ч из {paid_h} ч оплаченных\n\n"
        f"Администратор рассмотрит спор в течение 24 часов.\n\n"
        f"💡 Пока идёт рассмотрение — средства заморожены.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# dispute:detail:{dispute_id}
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^dispute:detail:(\d+)$"))
async def show_dispute_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать детали спора."""
    dispute_id = int((callback.data or "").split(":")[-1])

    dispute = await session.get(PlacementDispute, dispute_id)
    if not dispute:
        await callback.answer("❌ Спор не найден", show_alert=True)
        return

    req = await session.get(PlacementRequest, dispute.placement_request_id)
    channel = await session.get(TelegramChat, req.channel_id) if req else None

    reason_human = _REASON_LABELS.get(dispute.reason.value, dispute.reason.value)
    status_human = _STATUS_LABELS.get(dispute.status.value, dispute.status.value)

    text = (
        f"📋 *Спор #{dispute_id}*\n\n"
        f"📺 Канал: @{channel.username if channel else '—'}\n"
        f"🔍 Причина: *{reason_human}*\n"
        f"📊 Статус: {status_human}\n\n"
    )
    if dispute.owner_explanation:
        text += f"─── Объяснение владельца ───\n_{dispute.owner_explanation}_\n\n"
    if dispute.resolution:
        text += f"─── Решение ───\n*{dispute.resolution.value}*\n"
        if dispute.resolution_comment:
            text += f"_{dispute.resolution_comment}_\n"

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)

    builder = InlineKeyboardBuilder()
    if user and user.id == dispute.owner_id and dispute.status == DisputeStatus.open:
        builder.button(
            text="📝 Объяснить ситуацию",
            callback_data=f"dispute:owner_explain:{dispute_id}",
        )
    builder.button(text="🔙 Назад", callback_data="main:cabinet")
    builder.adjust(1)

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


# ---------------------------------------------------------------------------
# dispute:owner_explain:{dispute_id} — FSM объяснения владельца
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^dispute:owner_explain:(\d+)$"))
async def owner_explain_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать ввод объяснения владельца."""
    dispute_id = int((callback.data or "").split(":")[-1])
    await state.update_data(explaining_dispute_id=dispute_id)
    await state.set_state(DisputeStates.owner_explaining)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=f"dispute:detail:{dispute_id}")

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        "📝 *Объяснение ситуации*\n\n"
        "Опишите почему пост был удалён раньше срока.\n\n"
        "Примеры уважительных причин:\n"
        "• Технический сбой Telegram\n"
        "• Канал был атакован / взломан\n"
        "• Пост нарушал правила Telegram (запрос модерации)\n\n"
        "Введите объяснение (минимум 30 символов):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(DisputeStates.owner_explaining)
async def owner_explain_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Сохранить объяснение владельца."""
    explanation = (message.text or "").strip()

    if len(explanation) < 30:
        await message.answer("❌ Минимум 30 символов. Пожалуйста, опишите ситуацию подробнее.")
        return

    if not re.search(r"[а-яА-Яa-zA-Z]{5,}", explanation):
        await message.answer("❌ Объяснение должно быть осмысленным текстом.")
        return

    data = await state.get_data()
    dispute_id = data.get("explaining_dispute_id")
    if not dispute_id:
        await state.clear()
        return

    dispute = await session.get(PlacementDispute, dispute_id)
    if not dispute:
        await state.clear()
        await message.answer("❌ Спор не найден.")
        return

    dispute.owner_explanation = explanation
    dispute.status = DisputeStatus.owner_explained
    await session.commit()
    await state.clear()

    # Уведомить администраторов
    admins_result = await session.execute(select(User).where(User.is_admin == True))  # noqa: E712
    for admin in admins_result.scalars().all():
        try:
            builder_adm = InlineKeyboardBuilder()
            builder_adm.button(
                text="🔎 Рассмотреть спор",
                callback_data=f"admin:dispute:{dispute_id}",
            )
            if message.bot is None:
                continue
            await message.bot.send_message(
                chat_id=admin.telegram_id,
                text=(
                    f"📝 *Владелец объяснил ситуацию по спору #{dispute_id}*\n\n"
                    f"_{explanation}_\n\n"
                    f"Примите решение:"
                ),
                reply_markup=builder_adm.as_markup(),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Failed to send dispute notification to admin: {e}")

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Детали спора", callback_data=f"dispute:detail:{dispute_id}")

    await message.answer(
        "✅ *Объяснение принято!*\n\n"
        "Администратор рассмотрит ваше объяснение и примет решение в течение 24 часов.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
