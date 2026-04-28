"""Shared start handler."""

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.advertiser.adv_menu import adv_menu_kb
from src.bot.keyboards.owner.own_menu import own_menu_kb
from src.bot.keyboards.shared.main_menu import main_menu_kb, tos_kb
from src.config.settings import settings
from src.constants.fees import (
    PLATFORM_COMMISSION_RATE,
    PLATFORM_TOTAL_RATE,
    SERVICE_FEE_RATE,
    format_rate_pct,
)
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.user_repo import UserRepository

router = Router()

USER_NOT_FOUND = "Пользователь не найден."

_PLAN_NAMES = {
    "free": "Free",
    "starter": "Starter 🚀",
    "pro": "Pro 💎",
    "business": "Agency 🏢",
}

TOS_TEXT = (
    "📋 *Условия использования*\n\n"
    "Для продолжения необходимо принять условия использования платформы.\n\n"
    "🔹 Платформа не является налоговым агентом для владельцев каналов\n"
    "🔹 Вы самостоятельно несёте ответственность за уплату налогов\n"
    "🔹 Минимальный возраст: 18 лет\n\n"
    f"[Ознакомиться с полными условиями]({settings.terms_url})"
)

# MarkdownV2 escapes the `%` decimal point separator (comma) implicitly,
# but the `,` character itself is safe — only `.` would need escaping.
_PLATFORM_TOTAL = format_rate_pct(PLATFORM_TOTAL_RATE)
_PLATFORM_GROSS = format_rate_pct(PLATFORM_COMMISSION_RATE, 0)
_SERVICE_FEE = format_rate_pct(SERVICE_FEE_RATE)

WELCOME_TEXT = (
    "👋 Привет, *{first_name}*\\!\n\n"
    "Добро пожаловать в *RekHarborBot* — рекламную биржу Telegram\\-каналов\\.\n\n"
    "🔹 Рекламодатели размещают рекламу в каналах\n"
    "🔹 Владельцы каналов зарабатывают на публикациях\n"
    f"🔹 Комиссия платформы {_PLATFORM_TOTAL} "
    f"\\({_PLATFORM_GROSS} \\+ сервисный сбор {_SERVICE_FEE}\\)"
)


@router.message(Command("start"))
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка /start."""
    if message.from_user is None:
        return

    args = command.args

    # --- Parse REF_ referral code from deep link ---
    referral_code_from_start: str | None = None
    if args and args.startswith("REF_"):
        referral_code_from_start = args[4:]  # убираем "REF_"
    # --- end REF_ parsing ---

    # --- Video upload deep link (S7 addition) ---
    if args and args.startswith("upload_video_"):
        import redis.asyncio as aioredis

        from src.bot.states.placement import PlacementStates
        from src.config.settings import settings as _settings

        session_id = args.removeprefix("upload_video_")
        r = aioredis.from_url(str(_settings.redis_url))
        await r.setex(f"pending_video:{session_id}", 300, str(message.from_user.id))
        await r.aclose()  # type: ignore[attr-defined]
        await state.update_data(video_upload_session_id=session_id)
        await state.set_state(PlacementStates.upload_video)
        await message.answer("Отправьте видеофайл (до 2 минут, до 50 МБ):")
        return
    # --- end Video upload deep link ---

    telegram_id = message.from_user.id
    first_name = message.from_user.first_name or "User"

    user, is_new = await UserRepository(session).get_or_create(
        telegram_id,
        defaults={
            "username": message.from_user.username,
            "first_name": first_name,
            "referral_code": f"ref_{telegram_id}",
        },
    )

    # Register referral if new user and REF_ code was provided
    if is_new and referral_code_from_start:
        referrer = await UserRepository(session).get_by_referral_code(referral_code_from_start)
        if referrer and referrer.id != user.id:
            user.referred_by_id = referrer.id
            await session.flush()

    if user is None:
        return

    if user.terms_accepted_at is None:
        await message.answer(TOS_TEXT, reply_markup=tos_kb(), parse_mode="Markdown")
        return

    await message.answer(
        WELCOME_TEXT.format(first_name=first_name),
        reply_markup=main_menu_kb(),
        parse_mode="MarkdownV2",
    )


@router.message(Command("help"))
async def show_help_cmd(message: Message) -> None:
    """Показать помощь."""
    await message.answer("Помощь: /start — главное меню")


@router.callback_query(F.data == "terms:accept")
async def cb_tos_accept(callback: CallbackQuery, session: AsyncSession) -> None:
    """Принятие условий использования."""
    if not isinstance(callback.message, Message):
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return
    user.terms_accepted_at = datetime.now(UTC)
    first_name = callback.from_user.first_name or "User"
    await callback.message.edit_text(
        WELCOME_TEXT.format(first_name=first_name),
        reply_markup=main_menu_kb(),
        parse_mode="MarkdownV2",
    )
    await callback.answer()


@router.callback_query(F.data == "terms:decline")
async def cb_tos_decline(callback: CallbackQuery) -> None:
    """Отклонение условий использования."""
    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        "❌ Без принятия условий использование платформы невозможно.\n\n"
        "Если вы хотите продолжить, нажмите /start и примите условия.",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "main:main_menu")
async def cb_main_menu(callback: CallbackQuery) -> None:
    """Вернуться в главное меню."""
    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "main:adv_menu")
async def go_to_adv_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Перейти в меню рекламодателя (для кнопок «Назад»)."""
    if not isinstance(callback.message, Message):
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return
    plan_name = _PLAN_NAMES.get(user.plan, user.plan)
    await callback.message.edit_text(
        f"📣 *Меню рекламодателя*\n\n💳 Баланс: *{user.balance_rub} ₽* | ⭐ Тариф: *{plan_name}*",
        reply_markup=adv_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "main:own_menu")
async def go_to_own_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Перейти в меню владельца (для кнопок «Назад»)."""
    if not isinstance(callback.message, Message):
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return
    pending = await PlacementRequestRepository(session).get_pending_for_owner(user.id)
    await callback.message.edit_text(
        "📺 *Меню владельца канала*",
        reply_markup=own_menu_kb(pending_count=len(pending)),
        parse_mode="Markdown",
    )
    await callback.answer()
