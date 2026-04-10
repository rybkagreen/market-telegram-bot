"""Legal profile handler — redirects to web portal (152-ФЗ compliance)."""

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository

legal_profile_router = Router()

PORTAL_URL = "https://rekharbor.ru/portal"


@legal_profile_router.callback_query(F.data == "legal:start")
async def cb_legal_start(callback: CallbackQuery) -> None:
    """Redirect to web portal for legal profile (152-ФЗ)."""
    if not isinstance(callback.message, Message):
        return
    await callback.message.answer(
        "🔒 <b>Юридический профиль</b>\n\n"
        "Для защиты ваших персональных данных "
        "(Федеральный закон № 152-ФЗ) заполнение "
        "юридического профиля доступно только "
        "через защищённый веб-портал.\n\n"
        "Сервер портала расположен в России и "
        "соответствует требованиям Роскомнадзора.",
        reply_markup=legal_profile_redirect_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@legal_profile_router.callback_query(F.data == "legal:skip_first_start")
async def cb_legal_skip_first_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Skip legal profile prompt on first start."""
    if not isinstance(callback.message, Message):
        return
    db_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if db_user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    now = datetime.now(UTC)
    await session.execute(
        sa_update(User)
        .where(User.id == db_user.id)
        .values(legal_profile_prompted_at=now, legal_profile_skipped_at=now)
    )
    await session.commit()
    await state.clear()
    await callback.message.answer(
        f"Вы можете заполнить профиль позже через веб-портал:\n{PORTAL_URL}/legal-profile"
    )
    from src.bot.keyboards.shared.main_menu import main_menu_kb

    await callback.message.answer("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


@legal_profile_router.callback_query(F.data == "legal:skip")
async def cb_legal_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip legal profile."""
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.message.answer(
        f"Хорошо. Заполните профиль позже через веб-портал:\n{PORTAL_URL}/legal-profile"
    )
    await callback.answer()


@legal_profile_router.callback_query(F.data == "legal:edit")
async def cb_legal_edit(callback: CallbackQuery) -> None:
    """Edit legal profile — redirect to portal."""
    if not isinstance(callback.message, Message):
        return
    await callback.message.answer(
        f"✏️ Для редактирования профиля перейдите на веб-портал:\n{PORTAL_URL}/legal-profile",
        reply_markup=legal_profile_redirect_keyboard(),
    )
    await callback.answer()


@legal_profile_router.callback_query(F.data.startswith("legal:"))
async def cb_legal_any(callback: CallbackQuery) -> None:
    """Catch-all for any other legal callbacks — redirect to portal."""
    if not isinstance(callback.message, Message):
        return
    await callback.message.answer(
        f"🔒 Заполнение юридического профиля доступно на веб-портале:\n{PORTAL_URL}/legal-profile",
        reply_markup=legal_profile_redirect_keyboard(),
    )
    await callback.answer()


def legal_profile_redirect_keyboard():
    """Keyboard with portal redirect button."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Открыть портал",
                    url=f"{PORTAL_URL}/legal-profile",
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data="back_to_menu",
                )
            ],
        ]
    )
