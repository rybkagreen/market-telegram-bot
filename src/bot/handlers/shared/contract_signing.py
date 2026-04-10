"""Contract signing handler."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.shared.contract import contract_sign_keyboard
from src.core.services.contract_service import ContractService
from src.db.repositories.contract_repo import ContractRepo
from src.db.repositories.user_repo import UserRepository

contract_signing_router = Router()


@contract_signing_router.callback_query(F.data.regexp(r"^contract:view:\d+$"))
async def cb_contract_view(callback: CallbackQuery, session: AsyncSession) -> None:
    """Просмотр договора."""
    if not isinstance(callback.message, Message):
        return
    contract_id = int((callback.data or "").split(":")[2])
    contract = await ContractRepo(session).get_by_id(contract_id)
    if not contract:
        await callback.answer("Договор не найден", show_alert=True)
        return
    db_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if db_user is None or contract.user_id != db_user.id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    if contract.pdf_file_path:
        from pathlib import Path

        pdf = Path(contract.pdf_file_path)
        if pdf.exists():
            from aiogram.types import FSInputFile

            await callback.message.answer_document(
                FSInputFile(str(pdf)), caption=f"Договор №{contract_id}"
            )
        else:
            await callback.message.answer(
                f"📄 Договор №{contract_id}\nСтатус: {contract.contract_status}\nТип: {contract.contract_type}"
            )
    else:
        await callback.message.answer(
            f"📄 Договор №{contract_id}\n"
            f"Статус: {contract.contract_status}\n"
            f"Тип: {contract.contract_type}\n\n"
            f"PDF-версия будет доступна позже."
        )
    if contract.contract_status in ("pending", "draft"):
        await callback.message.answer(
            "Подписать договор:", reply_markup=contract_sign_keyboard(contract_id)
        )
    await callback.answer()


@contract_signing_router.callback_query(F.data.regexp(r"^contract:sign:\d+$"))
async def cb_contract_sign(callback: CallbackQuery, session: AsyncSession) -> None:
    """Подписать договор."""
    if not isinstance(callback.message, Message):
        return
    contract_id = int((callback.data or "").split(":")[2])
    db_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if db_user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    user_id = db_user.id
    svc = ContractService(session)
    try:
        contract = await svc.sign_contract(
            contract_id=contract_id, user_id=user_id, method="button_accept"
        )
        await session.commit()
        signed_str = contract.signed_at.strftime("%d.%m.%Y %H:%M") if contract.signed_at else "—"
        await callback.message.answer(
            f"✅ Договор №{contract_id} подписан.\nДата подписания: {signed_str}"
        )
    except PermissionError:
        await callback.answer("Нет доступа к этому договору", show_alert=True)
        return
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return
    await callback.answer()


@contract_signing_router.callback_query(F.data == "contract:accept_rules")
async def cb_accept_rules(callback: CallbackQuery, session: AsyncSession) -> None:
    """Принять правила платформы."""
    if not isinstance(callback.message, Message):
        return
    from datetime import UTC, datetime

    from sqlalchemy import update as sa_update

    from src.bot.keyboards.shared.legal_profile import first_start_legal_prompt_keyboard
    from src.db.models.user import User

    # Load by Telegram ID before service calls — accept_platform_rules needs DB user ID
    onboard_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if onboard_user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    svc = ContractService(session)
    await svc.accept_platform_rules(onboard_user.id)
    await session.commit()
    await callback.message.answer("✅ Правила платформы и политика конфиденциальности приняты.")

    # --- Continue onboarding flow (S7 addition) ---
    # Reload after commit to get fresh attribute values
    onboard_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if onboard_user is not None and onboard_user.legal_profile_prompted_at is None:
        now = datetime.now(UTC)
        await session.execute(
            sa_update(User).where(User.id == onboard_user.id).values(legal_profile_prompted_at=now)
        )
        await session.commit()
        await callback.message.answer(
            "📋 Заполните юридический профиль для работы с договорами и выплатами.",
            reply_markup=first_start_legal_prompt_keyboard(),
        )
    else:
        await callback.message.answer("✅ Добро пожаловать на платформу!")
    # --- end onboarding flow ---

    await callback.answer()
