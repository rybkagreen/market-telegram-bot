"""
Dispute handlers — арбитраж при досрочном удалении поста.
v4.3: Авто-открытие диспута если actual_duration < paid_duration * 0.80
"""

import logging
from contextlib import suppress
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.admin.admin import AdminCB
from src.bot.keyboards.shared.main_menu import MainMenuCB
from src.bot.states.dispute import DisputeStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.reputation_repo import ReputationRepo
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router(name="dispute")


# ══════════════════════════════════════════════════════════════
# ADVERTISER: Открытие диспута (окно 48ч после удаления)
# ══════════════════════════════════════════════════════════════


@router.callback_query(F.data.startswith("dispute:open:"))
async def open_dispute_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать открытие диспута рекламодателем (dispute:open:{placement_id})."""
    from sqlalchemy import select

    from src.db.models.placement_dispute import DisputeStatus, PlacementDispute
    from src.db.models.placement_request import PlacementStatus

    callback_data = callback.data
    if ":" not in callback_data:
        await callback.answer("❌ Неверный формат", show_alert=True)
        return

    try:
        placement_id = int(callback_data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ Неверный ID", show_alert=True)
        return

    async with async_session_factory() as session:
        placement = await session.get(PlacementRequest, placement_id)

        if not placement:
            await callback.answer("❌ Размещение не найдено", show_alert=True)
            return

        if placement.status != PlacementStatus.COMPLETED or not placement.deleted_at:
            await callback.answer("⏳ Пост ещё не удалён", show_alert=True)
            return

        now = datetime.now(UTC)
        hours_since_delete = (now - placement.deleted_at).total_seconds() / 3600

        if hours_since_delete > 48:
            await callback.answer("⏰ Окно диспута (48ч) истекло", show_alert=True)
            return

        stmt = select(PlacementDispute).where(
            PlacementDispute.placement_request_id == placement_id
        )
        result = await session.execute(stmt)
        existing_dispute = result.scalar_one_or_none()

        if existing_dispute:
            await callback.answer("ℹ️ Диспут уже открыт", show_alert=True)
            return

        dispute = PlacementDispute(
            placement_request_id=placement_id,
            opened_by="advertiser",
            reason="post_removed_early",
            status=DisputeStatus.OPEN,
            opened_at=now,
        )
        session.add(dispute)
        await session.flush()

        owner_id = placement.channel.owner_user_id if placement.channel else None
        if owner_id:
            from src.bot.handlers.shared.notifications import notify_dispute_opened_owner

            with suppress(Exception):
                await notify_dispute_opened_owner(callback.bot, owner_id, dispute)

        from src.config.settings import settings

        for admin_id in settings.admin_ids:
            from src.bot.handlers.shared.notifications import notify_admin_new_dispute

            with suppress(Exception):
                await notify_admin_new_dispute(callback.bot, admin_id, dispute)

        await callback.answer("✅ Диспут открыт", show_alert=True)


# ══════════════════════════════════════════════════════════════
# OWNER: Объяснение причины
# ══════════════════════════════════════════════════════════════


@router.callback_query(AdminCB.filter(F.action == "dispute_owner_explain"))
async def owner_explain_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать объяснение причины удаления владельцем."""
    dispute_id = callback.data.split(":")[-1]
    await state.update_data(dispute_id=dispute_id)
    await state.set_state(DisputeStates.owner_explaining)

    text = (
        "📝 <b>Объяснение причины удаления</b>\n\n"
        "Опишите почему пост был удалён раньше срока.\n"
        "<i>Минимум 30 символов</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())


@router.message(DisputeStates.owner_explaining)
async def owner_explain_text(message: Message, state: FSMContext) -> None:
    """Сохранить объяснение владельца."""
    explanation = message.text.strip()

    if len(explanation) < 30:
        await message.answer("❌ Минимум 30 символов")
        return

    data = await state.get_data()
    dispute_id = data.get("dispute_id")

    if not dispute_id:
        await state.clear()
        return

    async with async_session_factory() as session:

        from src.db.models.placement_dispute import PlacementDispute

        dispute = await session.get(PlacementDispute, int(dispute_id))
        if not dispute:
            await state.clear()
            return

        dispute.owner_explanation = explanation
        dispute.owner_explained_at = datetime.now(UTC)
        await session.flush()

        from src.config.settings import settings

        for admin_id in settings.admin_ids:
            text = f"📢 Объяснение по диспуту #{dispute.id}: {explanation[:200]}..."
            with suppress(Exception):
                await message.bot.send_message(admin_id, text)

    await message.answer("✅ Объяснение сохранено")
    await state.clear()


# ══════════════════════════════════════════════════════════════
# ADMIN: Просмотр и решение
# ══════════════════════════════════════════════════════════════


@router.callback_query(AdminCB.filter(F.action == "disputes"))
async def admin_disputes_list(callback: CallbackQuery) -> None:
    """Показать список открытых диспутов."""
    from sqlalchemy import select

    from src.db.models.placement_dispute import DisputeStatus, PlacementDispute

    async with async_session_factory() as session:
        stmt = select(PlacementDispute).where(
            PlacementDispute.status == DisputeStatus.OPEN
        ).order_by(PlacementDispute.opened_at.desc())

        result = await session.execute(stmt)
        disputes = list(result.scalars().all())

    if not disputes:
        text = "📭 <b>Нет открытых диспутов</b>"
    else:
        text = f"📋 <b>Открытые диспуты ({len(disputes)})</b>\n\n"
        for d in disputes[:10]:
            text += f"• #{d.id} — {d.reason}\n"

    builder = InlineKeyboardBuilder()
    for d in disputes[:10]:
        builder.button(text=f"#{d.id}", callback_data=f"admin:dispute:{d.id}")
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="admin_panel"))
    builder.adjust(1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())


@router.callback_query(AdminCB.filter(F.action == "dispute"))
async def admin_review_dispute(callback: CallbackQuery) -> None:
    """Просмотр деталей диспута."""
    dispute_id = int(callback.data.split(":")[-1])

    async with async_session_factory() as session:
        from src.db.models.placement_dispute import PlacementDispute

        dispute = await session.get(PlacementDispute, dispute_id)
        if not dispute:
            await callback.answer("❌ Не найден", show_alert=True)
            return

        placement = await session.get(PlacementRequest, dispute.placement_request_id)
        channel = placement.channel if placement else None

        text = f"📋 <b>Диспут #{dispute.id}</b>\n\n"
        text += f"Статус: {dispute.status.value}\n"
        text += f"Причина: {dispute.reason}\n"
        text += f"Дата: {dispute.opened_at.strftime('%d.%m.%Y %H:%M')}\n"

        if channel:
            text += f"Канал: @{channel.username or channel.title}\n"
        if dispute.owner_explanation:
            text += f"\n📝 Объяснение: {dispute.owner_explanation}\n"

        text += "\n<b>Решение:</b>"

        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔴 Вина владельца (100% возврат)",
            callback_data=f"admin:dispute:resolve:owner_fault:{dispute_id}",
        )
        builder.button(
            text="🟡 Вина рекламодателя (85% владельцу)",
            callback_data=f"admin:dispute:resolve:advertiser_fault:{dispute_id}",
        )
        builder.button(
            text="⚪ Тех.ошибка (100% возврат)",
            callback_data=f"admin:dispute:resolve:technical:{dispute_id}",
        )
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="disputes").pack())
        builder.adjust(1)

        await safe_callback_edit(callback, text, reply_markup=builder.as_markup())


@router.callback_query(AdminCB.filter(F.action == "dispute:resolve"))
async def admin_resolve_dispute(callback: CallbackQuery) -> None:
    """Исполнить решение администратора."""
    parts = callback.data.split(":")
    if len(parts) < 5:
        await callback.answer("❌ Неверный формат", show_alert=True)
        return

    resolution_type = parts[3]
    dispute_id = int(parts[4])

    async with async_session_factory() as session:
        from src.core.services.billing_service import BillingService
        from src.core.services.reputation_service import ReputationService
        from src.db.models.placement_dispute import DisputeStatus, PlacementDispute

        dispute = await session.get(PlacementDispute, dispute_id)
        if not dispute:
            await callback.answer("❌ Не найден", show_alert=True)
            return

        placement = await session.get(PlacementRequest, dispute.placement_request_id)
        if not placement:
            await callback.answer("❌ Не найдено", show_alert=True)
            return

        billing_service = BillingService()
        rep_service = ReputationService(session, ReputationRepo(session))

        final_price = placement.final_price or placement.proposed_price
        advertiser_id = placement.advertiser_id
        owner_id = placement.channel.owner_user_id if placement.channel else 0

        if resolution_type == "owner_fault":
            await billing_service.refund_escrow_full(
                session, placement.id, "dispute_owner_fault"
            )
            await rep_service.apply_event(session, owner_id, "owner", "dispute_owner_fault")
            resolution_text = "Вина владельца — 100% возврат"

        elif resolution_type == "advertiser_fault":
            await billing_service.release_escrow(
                session, placement.id, final_price, advertiser_id, owner_id
            )
            await rep_service.apply_event(
                session, advertiser_id, "advertiser", "dispute_advertiser_fault"
            )
            resolution_text = "Вина рекламодателя — 85% владельцу"

        elif resolution_type == "technical":
            await billing_service.refund_escrow_full(
                session, placement.id, "dispute_technical"
            )
            resolution_text = "Тех.ошибка — 100% возврат"

        else:
            await callback.answer("❌ Неверный тип", show_alert=True)
            return

        dispute.status = DisputeStatus.RESOLVED
        dispute.resolved_at = datetime.now(UTC)
        dispute.resolution = resolution_type
        await session.flush()

        try:
            from src.bot.handlers.shared.notifications import notify_dispute_resolved

            await notify_dispute_resolved(
                callback.bot, advertiser_id, owner_id, dispute, resolution_text
            )
        except Exception as e:
            logger.error(f"Notify error: {e}")

    await callback.answer(f"✅ {resolution_text}", show_alert=True)


__all__ = ["router"]
