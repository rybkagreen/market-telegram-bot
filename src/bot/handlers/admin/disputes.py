"""Admin disputes handler — рассмотрение споров."""

import contextlib
import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers.disputes import resolve_dispute_admin as api_resolve_dispute_admin
from src.api.schemas.admin import DisputeResolveRequest
from src.bot.filters.admin import AdminFilter
from src.bot.handlers.shared.notifications import notify_dispute_resolved
from src.constants.fees import (
    OWNER_NET_RATE,
    OWNER_SHARE_RATE,
    SERVICE_FEE_RATE,
    format_rate_pct,
)
from src.core.services.placement_transition_service import (
    InvalidTransitionError,
    TransitionInvariantError,
)
from src.db.models.dispute import DisputeStatus, PlacementDispute
from src.db.models.placement_request import PlacementRequest
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

_FORMAT_HOURS = {
    "post_24h": 24,
    "post_48h": 48,
    "post_7d": 168,
    "pin_24h": 24,
    "pin_48h": 48,
}

_RESOLUTION_LABELS = {
    "owner_fault": "Вина владельца — 100% возврат рекламодателю",
    "advertiser_fault": "Жалоба необоснована — выплата владельцу",
    "technical": "Техническая ошибка — 100% возврат рекламодателю",
    "partial": "Частичный возврат (50/50)",
}

# ---------------------------------------------------------------------------
# admin:disputes — список открытых споров
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "admin:disputes", AdminFilter())
async def admin_disputes_list(callback: CallbackQuery, session: AsyncSession) -> None:
    """Список открытых споров."""
    if not isinstance(callback.message, Message):
        return
    disputes = await DisputeRepository(session).get_open()

    builder = InlineKeyboardBuilder()
    for d in disputes[:10]:
        icon = "🔴" if d.status == DisputeStatus.open else "🟡"
        builder.button(
            text=f"{icon} Спор #{d.id}",
            callback_data=f"admin:dispute:{d.id}",
        )
    builder.button(text="🔙 Назад", callback_data="admin:panel")
    builder.adjust(1)

    await callback.message.edit_text(
        f"🚨 *Открытые споры*\n\nВсего: *{len(disputes)}*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# admin:dispute:{id} — детали спора для администратора
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^admin:dispute:(\d+)$"), AdminFilter())
async def admin_review_dispute(callback: CallbackQuery, session: AsyncSession) -> None:
    """Детали спора для принятия решения."""
    if not isinstance(callback.message, Message):
        return
    dispute_id = int((callback.data or "").split(":")[-1])

    dispute = await session.get(PlacementDispute, dispute_id)
    if not dispute:
        await callback.answer("❌ Спор не найден", show_alert=True)
        return

    req = await session.get(PlacementRequest, dispute.placement_request_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    from src.db.models.telegram_chat import TelegramChat

    channel = await session.get(TelegramChat, req.channel_id)
    price = req.final_price if req.final_price is not None else req.proposed_price

    fmt_val = (
        req.publication_format.value
        if hasattr(req.publication_format, "value")
        else str(req.publication_format)
    )
    paid_h = _FORMAT_HOURS.get(fmt_val, 24)
    actual_h = 0
    if req.published_at and req.deleted_at:
        delta = req.deleted_at - req.published_at
        actual_h = max(0, int(delta.total_seconds() / 3600))
    life_pct = min(100, int(actual_h / paid_h * 100)) if paid_h else 0

    published = req.published_at.strftime("%d.%m %H:%M") if req.published_at else "—"
    deleted = req.deleted_at.strftime("%d.%m %H:%M") if req.deleted_at else "—"

    owner_expl = (
        f"_{dispute.owner_explanation}_"
        if dispute.owner_explanation
        else "_Объяснение не предоставлено_"
    )
    adv_comment = (
        f"_{dispute.advertiser_comment}_" if dispute.advertiser_comment else "_Нет комментария_"
    )

    builder = InlineKeyboardBuilder()
    for verdict, label in [
        ("owner_fault", "✅ Вина владельца → 100% рекламодателю"),
        ("partial", "⚖️ Частичный возврат (50/50)"),
        ("advertiser_fault", "❌ Жалоба необоснована → выплатить владельцу"),
        ("technical", "🔧 Техническая ошибка → 100% рекламодателю"),
    ]:
        builder.button(
            text=label,
            callback_data=f"admin:dispute:resolve:{verdict}:{dispute_id}",
        )
    builder.button(text="🔙 Список споров", callback_data="admin:disputes")
    builder.adjust(1)

    await callback.message.edit_text(
        f"🚨 *Спор #{dispute_id}*\n\n"
        f"─── Детали ───\n"
        f"Канал: @{channel.username if channel else '—'}\n"
        f"Формат: {fmt_val}\n"
        f"Эскроу: *{price:.0f} ₽*\n"
        f"Опубликовано: {published}\n"
        f"Удалено: {deleted}\n"
        f"Прожило: {actual_h}ч / {paid_h}ч ({life_pct}%)\n\n"
        f"─── Позиция владельца ───\n{owner_expl}\n\n"
        f"─── Позиция рекламодателя ───\n{adv_comment}\n\n"
        f"Примите решение:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# admin:dispute:resolve:{verdict}:{dispute_id} — вынести решение
# ---------------------------------------------------------------------------


@router.callback_query(
    F.data.regexp(
        r"^admin:dispute:resolve:(owner_fault|advertiser_fault|technical|partial):(\d+)$"
    ),
    AdminFilter(),
)
async def admin_resolve_dispute(callback: CallbackQuery, session: AsyncSession) -> None:
    """Вынести решение по спору."""
    if not isinstance(callback.message, Message):
        return
    parts = (callback.data or "").split(":")
    verdict = parts[3]
    dispute_id = int(parts[4])

    dispute = await session.get(PlacementDispute, dispute_id)
    if not dispute:
        await callback.answer("❌ Спор не найден", show_alert=True)
        return

    req = await session.get(PlacementRequest, dispute.placement_request_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    price = req.final_price if req.final_price is not None else req.proposed_price

    # Compute outcome strings for UI (independent of billing — same business rules).
    if verdict in ("owner_fault", "technical"):
        advertiser_outcome = f"✅ Возврат: *{price:.0f} ₽* (100%)"
        owner_outcome = "❌ Средства возвращены рекламодателю"
    elif verdict == "advertiser_fault":
        # Промт 15.7: net = 80% gross − 1.5% сервисный сбор (= OWNER_NET_RATE).
        owner_gross = price * OWNER_SHARE_RATE
        service_fee = owner_gross * SERVICE_FEE_RATE
        owner_amount = (owner_gross - service_fee).quantize(Decimal("0.01"))
        advertiser_outcome = "❌ Жалоба признана необоснованной. Возврата нет."
        owner_outcome = (
            f"✅ Выплата: *{owner_amount:.0f} ₽* "
            f"({format_rate_pct(OWNER_NET_RATE)})"
        )
    else:  # partial
        half = (price * Decimal("0.5")).quantize(Decimal("0.01"))
        advertiser_outcome = f"🔓 Частичный возврат: *{half:.0f} ₽* (~50%)"
        owner_outcome = f"💰 Частичная выплата: ~*{half:.0f} ₽* (~50%)"

    # Resolve admin user — required by API endpoint.
    admin_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not admin_user:
        await callback.answer("❌ Admin user not resolvable", show_alert=True)
        return

    # Delegate to API endpoint (Decision 11 — sync canonical path).
    # Shares the session, so router-level commit applies to bot's mutations too.
    body = DisputeResolveRequest(
        resolution=verdict,
        admin_comment=None,
        custom_split_percent=50 if verdict == "partial" else None,
    )
    try:
        await api_resolve_dispute_admin(
            dispute_id=dispute_id,
            body=body,
            admin_user=admin_user,
            session=session,
        )
    except HTTPException as exc:
        logger.error("admin dispute resolve API error: %s", exc.detail)
        await callback.answer(f"❌ {exc.detail}", show_alert=True)
        return
    except (InvalidTransitionError, TransitionInvariantError) as exc:
        logger.error("admin dispute resolve transition error: %s", exc)
        await callback.answer("❌ Не удалось обновить статус", show_alert=True)
        return

    resolution_label = _RESOLUTION_LABELS[verdict]

    # Уведомить обе стороны
    advertiser = await session.get(User, req.advertiser_id)
    owner = await session.get(User, req.owner_id)
    for user, outcome in [(advertiser, advertiser_outcome), (owner, owner_outcome)]:
        if user and callback.bot:
            with contextlib.suppress(Exception):
                await notify_dispute_resolved(
                    bot=callback.bot,
                    telegram_id=user.telegram_id,
                    dispute_id=dispute_id,
                    resolution=f"{resolution_label}\n\n{outcome}",
                )

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список споров", callback_data="admin:disputes")

    await callback.message.edit_text(
        f"✅ *Спор #{dispute_id} разрешён*\n\n"
        f"Решение: *{resolution_label}*\n\n"
        f"Рекламодатель: {advertiser_outcome}\n"
        f"Владелец: {owner_outcome}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()
