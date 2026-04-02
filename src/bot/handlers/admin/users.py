"""Admin users handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.admin import AdminFilter
from src.bot.keyboards.admin.admin import admin_menu_kb
from src.bot.utils.safe_callback import safe_callback_edit

router = Router()


@router.message(Command("admin"), AdminFilter())
async def cmd_admin(message: Message) -> None:
    """Админ панель."""
    await message.answer("🔧 Админ панель", reply_markup=admin_menu_kb())


@router.callback_query(lambda c: c.data == "admin:platform")
async def show_platform_account(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать аккаунт платформы."""
    from src.db.repositories.platform_account_repo import PlatformAccountRepository

    account = await PlatformAccountRepository(session).get_platform_account()
    if account:
        text = (
            f"🏦 Платформа\n"
            f"Эскроу (зарезервировано): {account.escrow_reserved:.2f} ₽\n"
            f"К выплате владельцам: {account.payout_reserved:.2f} ₽\n"
            f"Прибыль платформы: {account.profit_accumulated:.2f} ₽\n"
            f"Всего пополнений: {account.total_topups:.2f} ₽\n"
            f"Всего выплат: {account.total_payouts:.2f} ₽"
        )
    else:
        text = "🏦 Платформа\nДанные недоступны"
    await safe_callback_edit(callback, text)


@router.callback_query(lambda c: c.data == "admin:payouts")
async def show_pending_payouts(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать ожидающие выплаты."""
    from src.db.repositories.payout_repo import PayoutRepository

    payouts = await PayoutRepository(session).get_pending()
    if not payouts:
        await callback.answer("Нет ожидающих выплат", show_alert=True)
        return

    lines = [f"💸 Ожидающие выплаты ({len(payouts)}):"]
    for p in payouts[:10]:
        lines.append(f"• #{p.id} — {p.gross_amount:.2f} ₽ (owner_id={p.owner_id})")
    await safe_callback_edit(callback, "\n".join(lines))


@router.callback_query(lambda c: c.data.startswith("admin:approve_payout:"))
async def approve_payout(callback: CallbackQuery) -> None:
    """Одобрить выплату."""
    await callback.answer("Выплата одобрена", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("admin:reject_payout:"))
async def reject_payout(callback: CallbackQuery) -> None:
    """Отклонить выплату."""
    await callback.answer("Выплата отклонена", show_alert=True)
