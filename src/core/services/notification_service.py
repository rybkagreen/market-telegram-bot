"""
Notification Service для уведомлений пользователей.
Интегрируется с mailing_service и billing_service.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.notification_tasks import notify_user

logger = logging.getLogger(__name__)


@dataclass
class CampaignStats:
    """Статистика кампании для уведомления."""

    total_sent: int
    total_failed: int
    total_skipped: int
    success_rate: float
    total_cost: Decimal


class NotificationService:
    """
    Сервис уведомлений пользователей.

    Методы:
        notify_campaign_started: Уведомить о начале кампании
        notify_campaign_done: Уведомить о завершении кампании
        notify_campaign_error: Уведомить об ошибке кампании
        notify_low_balance: Уведомить о низком балансе
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""

    async def notify_campaign_started(self, user_id: int, campaign_id: int) -> bool:
        """
        Уведомить пользователя о начале кампании.

        Args:
            user_id: ID пользователя.
            campaign_id: ID кампании.

        Returns:
            True если уведомление отправлено.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if user is None:
                logger.error(f"User {user_id} not found")
                return False

        message = (
            f"🚀 <b>Кампания запущена!</b>\n\n"
            f"Ваша рекламная кампания начала рассылку.\n"
            f"ID кампании: {campaign_id}\n\n"
            f"Вы получите уведомление о завершении."
        )

        try:
            notify_user.delay(
                telegram_id=user.telegram_id,
                message=message,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"Error notifying campaign started: {e}")
            return False

    async def notify_campaign_done(
        self,
        user_id: int,
        campaign_id: int,
        stats: CampaignStats,
    ) -> bool:
        """
        Уведомить пользователя о завершении кампании.

        Args:
            user_id: ID пользователя.
            campaign_id: ID кампании.
            stats: Статистика кампании.

        Returns:
            True если уведомление отправлено.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if user is None:
                logger.error(f"User {user_id} not found")
                return False

        message = (
            f"✅ <b>Кампания завершена!</b>\n\n"
            f"ID кампании: {campaign_id}\n\n"
            f"📊 <b>Результаты:</b>\n"
            f"• Отправлено: {stats.total_sent}\n"
            f"• Не удалось: {stats.total_failed}\n"
            f"• Пропущено: {stats.total_skipped}\n"
            f"• Success rate: {stats.success_rate:.1f}%\n\n"
            f"💰 <b>Стоимость:</b> {stats.total_cost} RUB\n\n"
            f"Используйте /analytics для подробной статистики."
        )

        try:
            notify_user.delay(
                telegram_id=user.telegram_id,
                message=message,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"Error notifying campaign done: {e}")
            return False

    async def notify_campaign_error(
        self,
        user_id: int,
        campaign_id: int,
        error_msg: str,
    ) -> bool:
        """
        Уведомить пользователя об ошибке кампании.

        Args:
            user_id: ID пользователя.
            campaign_id: ID кампании.
            error_msg: Сообщение об ошибке.

        Returns:
            True если уведомление отправлено.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if user is None:
                logger.error(f"User {user_id} not found")
                return False

        message = (
            f"❌ <b>Ошибка кампании!</b>\n\n"
            f"ID кампании: {campaign_id}\n\n"
            f"Ошибка: {error_msg}\n\n"
            f"Попробуйте запустить кампанию снова или обратитесь в поддержку."
        )

        try:
            notify_user.delay(
                telegram_id=user.telegram_id,
                message=message,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"Error notifying campaign error: {e}")
            return False

    async def notify_low_balance(self, user_id: int, balance: Decimal) -> bool:
        """
        Уведомить пользователя о низком балансе.

        Args:
            user_id: ID пользователя.
            balance: Текущий баланс.

        Returns:
            True если уведомление отправлено.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if user is None:
                logger.error(f"User {user_id} not found")
                return False

        message = (
            f"⚠️ <b>Низкий баланс</b>\n\n"
            f"Ваш баланс: {balance} RUB\n"
            f"Пополните баланс для продолжения использования бота.\n\n"
            f"Используйте команду /billing для пополнения."
        )

        try:
            notify_user.delay(
                telegram_id=user.telegram_id,
                message=message,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"Error notifying low balance: {e}")
            return False

    async def notify_referral_bonus(
        self,
        user_id: int,
        bonus_amount: Decimal,
        referred_user_id: int,
    ) -> bool:
        """
        Уведомить о бонусе за реферала.

        Args:
            user_id: ID пользователя.
            bonus_amount: Сумма бонуса.
            referred_user_id: ID приглашённого пользователя.

        Returns:
            True если уведомление отправлено.
        """
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(user_id)

            if user is None:
                logger.error(f"User {user_id} not found")
                return False

        message = (
            f"🎁 <b>Реферальный бонус!</b>\n\n"
            f"Ваш друг пополнил баланс.\n"
            f"Бонус: +{bonus_amount} RUB\n\n"
            f"Спасибо за приглашение!"
        )

        try:
            notify_user.delay(
                telegram_id=user.telegram_id,
                message=message,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"Error notifying referral bonus: {e}")
            return False


# Глобальный экземпляр
notification_service = NotificationService()


# ─── BL-107 Phase B.5a — admin review notifications ────────────────────────


async def notify_admins_evidence_submitted(
    session: AsyncSession,
    channel_id: int,
    owner_user_id: int,
    application_number: str,
) -> int:
    """Notify all admins что owner submitted blogger registry evidence.

    BL-107 Phase B.5a — manual evidence path. Fires when owner posts
    к POST /api/channels/{id}/submit-registry-evidence.

    Returns count of admins notified (для logging / tests).
    Session is read-only — no commit done here (caller-owns per S-48).
    """
    user_repo = UserRepository(session)
    admins = await user_repo.get_all_admins()

    message = (
        f"📋 <b>Новая заявка на верификацию канала</b>\n\n"
        f"Канал ID: <code>{channel_id}</code>\n"
        f"Владелец ID: <code>{owner_user_id}</code>\n"
        f"Номер заявления: <code>{application_number}</code>\n\n"
        f"Откройте админ-панель для рассмотрения."
    )

    notified = 0
    for admin in admins:
        try:
            notify_user.delay(
                telegram_id=admin.telegram_id,
                message=message,
                parse_mode="HTML",
            )
            notified += 1
        except Exception as e:
            logger.error(f"Error notifying admin {admin.id} about evidence submitted: {e}")

    return notified


async def notify_owner_verification_decided(
    session: AsyncSession,
    owner_user_id: int,
    channel_id: int,
    decision: Literal["verified", "rejected"],
    reason: str | None = None,
) -> bool:
    """Notify channel owner о admin's verify/reject decision.

    BL-107 Phase B.5a — manual evidence path outcome notification.
    Session is read-only — no commit done here (caller-owns per S-48).
    """
    user_repo = UserRepository(session)
    owner = await user_repo.get_by_id(owner_user_id)
    if owner is None:
        logger.error(f"Owner user {owner_user_id} not found — cannot notify")
        return False

    if decision == "verified":
        message = (
            f"✅ <b>Канал верифицирован!</b>\n\n"
            f"Канал ID: <code>{channel_id}</code>\n\n"
            f"Ваш канал зарегистрирован в Реестре блогеров. "
            f"Теперь вы можете принимать заявки на размещение."
        )
    else:
        reason_block = f"\n\n<b>Причина:</b> {reason}" if reason else ""
        message = (
            f"❌ <b>Заявка на верификацию отклонена</b>\n\n"
            f"Канал ID: <code>{channel_id}</code>"
            f"{reason_block}\n\n"
            f"Вы можете подать заявку повторно с обновлёнными данными."
        )

    try:
        notify_user.delay(
            telegram_id=owner.telegram_id,
            message=message,
            parse_mode="HTML",
        )
        return True
    except Exception as e:
        logger.error(f"Error notifying owner {owner_user_id} about verification decision: {e}")
        return False


# ─── BL-107 Phase B.6 — periodic re-verification notifications ──────────────


async def notify_owner_verification_lost(
    session: AsyncSession,
    owner_user_id: int,
    channel_id: int,
) -> bool:
    """Notify channel owner что Trustchannelbot verification was automatically lost.

    BL-107 Phase B.6 — background periodic check detected что @Trustchannelbot
    больше не admin канала, и verification was reset. Owner может либо
    re-add Trustchannelbot, либо submit manual evidence через mini_app.

    Session is read-only — no commit done here (caller-owns per S-48).
    """
    user_repo = UserRepository(session)
    owner = await user_repo.get_by_id(owner_user_id)
    if owner is None:
        logger.error(f"Owner user {owner_user_id} not found — cannot notify")
        return False

    message = (
        f"⚠️ <b>Верификация канала сброшена</b>\n\n"
        f"Канал ID: <code>{channel_id}</code>\n\n"
        f"@Trustchannelbot больше не является администратором канала, "
        f"поэтому автоматическая верификация в Реестре блогеров (ФЗ-303) "
        f"была отозвана.\n\n"
        f"Чтобы восстановить статус, добавьте @Trustchannelbot обратно "
        f"в администраторы канала или подайте заявку вручную через "
        f"раздел «Реестр блогеров» в mini app."
    )

    try:
        notify_user.delay(
            telegram_id=owner.telegram_id,
            message=message,
            parse_mode="HTML",
        )
        return True
    except Exception as e:
        logger.error(f"Error notifying owner {owner_user_id} about verification lost: {e}")
        return False
