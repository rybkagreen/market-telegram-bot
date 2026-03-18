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
    # TODO: Get PlatformAccount
    text = "🏦 Платформа\nБаланс: 0 ₽"
    await safe_callback_edit(callback, text)


@router.callback_query(lambda c: c.data == "admin:payouts")
async def show_pending_payouts(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать ожидающие выплаты."""
    # TODO: Get pending payouts
    await callback.answer("Выплаты", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("admin:approve_payout:"))
async def approve_payout(callback: CallbackQuery) -> None:
    """Одобрить выплату."""
    await callback.answer("Выплата одобрена", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("admin:reject_payout:"))
async def reject_payout(callback: CallbackQuery) -> None:
    """Отклонить выплату."""
    await callback.answer("Выплата отклонена", show_alert=True)
