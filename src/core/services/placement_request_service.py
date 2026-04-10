"""
PlacementRequest Service — оркестратор всего флоу создания и исполнения заявки.
"""

import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.reputation_repo import ReputationRepo
from src.tasks.notification_tasks import notify_owner_new_placement_task

if TYPE_CHECKING:
    from src.core.services.billing_service import BillingService

logger = logging.getLogger(__name__)

PLACEMENT_NOT_FOUND = "Placement not found"
CHANNEL_NOT_BELONG = "Channel does not belong to owner"
PLACEMENT_NOT_BELONG = "Placement does not belong to advertiser"


# =============================================================================
# УВЕДОМЛЕНИЯ (импортируются здесь для избежания circular imports)
# =============================================================================


async def _notify_create_request(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel: TelegramChat,
) -> None:
    """Отправить уведомление о новой заявке."""
    try:
        from src.bot.handlers.shared.notifications import notify_new_request

        await notify_new_request(
            placement, advertiser, owner, channel.username or f"ID:{channel.id}"
        )
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_owner_accept(
    placement: PlacementRequest,
    advertiser: User,
    channel: TelegramChat,
) -> None:
    """Отправить уведомление о принятии заявки владельцем."""
    try:
        from src.bot.handlers.shared.notifications import notify_owner_accepted

        await notify_owner_accepted(placement, advertiser, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_counter_offer(
    placement: PlacementRequest,
    advertiser: User,
    channel: TelegramChat,
) -> None:
    """Отправить уведомление о контр-предложении."""
    try:
        from src.bot.handlers.shared.notifications import notify_counter_offer

        await notify_counter_offer(placement, advertiser, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_counter_accepted(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel: TelegramChat,
) -> None:
    """Отправить уведомление о принятии контр-предложения."""
    try:
        from src.bot.handlers.shared.notifications import notify_counter_accepted

        await notify_counter_accepted(
            placement, advertiser, owner, channel.username or f"ID:{channel.id}"
        )
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_payment_received(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel: TelegramChat,
) -> None:
    """Отправить уведомление о получении оплаты."""
    try:
        from src.bot.handlers.shared.notifications import notify_payment_received
        from src.bot.main import bot
        from src.constants.payments import OWNER_SHARE

        if bot is None:
            return

        earned_rub = (placement.final_price or placement.proposed_price) * OWNER_SHARE
        await notify_payment_received(
            bot, owner.telegram_id, earned_rub, channel.username or f"ID:{channel.id}"
        )
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_rejected(
    placement: PlacementRequest,
    advertiser: User,
    channel: TelegramChat,
) -> None:
    """Отправить уведомление об отклонении заявки."""
    try:
        from src.bot.handlers.shared.notifications import notify_rejected

        await notify_rejected(placement, advertiser, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_cancelled(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel: TelegramChat,
    reputation_delta: float = 0.0,
) -> None:
    """Отправить уведомление об отмене заявки."""
    try:
        from src.bot.handlers.shared.notifications import notify_cancelled

        await notify_cancelled(
            placement, advertiser, owner, channel.username or f"ID:{channel.id}", reputation_delta
        )
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


class PlacementRequestService:
    """
    Сервис для управления заявками на размещение.

    Методы:
        create_request: Создать заявку
        owner_accept: Владелец принял
        owner_reject: Владелец отклонил
        owner_counter_offer: Контр-предложение
        advertiser_accept_counter: Рекламодатель принял контр
        advertiser_cancel: Рекламодатель отменил
        process_payment: Оплата
        process_publication_success: Публикация успешна
        process_publication_failure: Ошибка публикации
        auto_expire: Авто-отклонение по истечении
        validate_rejection_reason: Валидация комментария
    """

    def __init__(
        self,
        session: AsyncSession,
        placement_repo: PlacementRequestRepository,
        channel_settings_repo: ChannelSettingsRepo,
        reputation_repo: ReputationRepo,
        billing_service: "BillingService | None" = None,
    ):
        """
        Инициализация сервиса.

        Args:
            session: Асинхронная сессия SQLAlchemy.
            placement_repo: Репозиторий заявок.
            channel_settings_repo: Репозиторий настроек каналов.
            reputation_repo: Репозиторий репутации.
            billing_service: Сервис платежей (опционально для create_request).
        """
        self.session = session
        self.placement_repo = placement_repo
        self.channel_settings_repo = channel_settings_repo
        self.reputation_repo = reputation_repo
        self.billing_service = billing_service

    async def create_request(
        self,
        advertiser_id: int,
        channel_id: int,
        proposed_price: Decimal,
        final_text: str,
        proposed_schedule: datetime | None = None,
        proposed_frequency: int | None = None,
        campaign_id: int | None = None,
        is_test: bool = False,
        test_label: str | None = None,
        publication_format: str | None = None,
    ) -> PlacementRequest:
        """
        Создать заявку на размещение.

        Проверки перед созданием:
        1. advertiser не заблокирован (ReputationScore.is_advertiser_blocked)
        2. proposed_price >= ChannelSettings.MIN_PRICE_PER_POST (100 кр)
        3. channel_id существует и активен

        Args:
            advertiser_id: ID рекламодателя.
            campaign_id: ID кампании.
            channel_id: ID канала.
            proposed_price: Предлагаемая цена.
            final_text: Финальный текст рекламы.
            proposed_schedule: Желаемое время публикации.
            proposed_frequency: Частота (для пакетов).
            is_test: Флаг тестовой кампании (без оплаты).
            test_label: Пометка тестовой кампании.

        Returns:
            Созданная заявка.

        Raises:
            ValueError: Если проверки не пройдены.
        """
        from src.db.models.telegram_chat import TelegramChat

        # Проверка 1: advertiser не заблокирован
        rep_score = await self.reputation_repo.get_by_user(advertiser_id)
        if (
            rep_score
            and rep_score.is_advertiser_blocked
            and rep_score.advertiser_blocked_until
            and rep_score.advertiser_blocked_until > datetime.now(UTC)
        ):
            raise ValueError("Advertiser is blocked")

        # Проверка 2: цена >= минимальной
        from src.constants.payments import MIN_PRICE_PER_POST as _MIN_PRICE

        if proposed_price < _MIN_PRICE:
            raise ValueError(f"Price must be >= {_MIN_PRICE}")

        # Проверка 3: channel существует и активен
        channel = await self.session.get(TelegramChat, channel_id)
        if not channel or not channel.is_active:
            raise ValueError("Channel not found or inactive")

        # Создаём заявку
        placement = await self.placement_repo.create_placement(
            advertiser_id=advertiser_id,
            campaign_id=campaign_id,
            channel_id=channel_id,
            proposed_price=proposed_price,
            final_text=final_text,
            proposed_schedule=proposed_schedule,
            proposed_frequency=proposed_frequency,
            is_test=is_test,
            test_label=test_label,
            publication_format=publication_format,
        )

        # Отправляем уведомление владельцу через Celery (API и bot — разные контейнеры)
        try:
            notify_owner_new_placement_task.apply_async(
                args=[placement.id],
                queue="notifications",
            )
        except Exception as e:
            logger.error(f"Failed to enqueue notification for placement {placement.id}: {e}")

        return placement

    async def owner_accept(
        self,
        placement_id: int,
        owner_id: int,
        final_price: Decimal | None = None,
        final_schedule: datetime | None = None,
    ) -> PlacementRequest:
        """
        Владелец принял заявку.

        Проверки:
        1. Заявка существует и принадлежит каналу owner_id
        2. Статус == pending_owner
        3. expires_at не истёк

        Args:
            placement_id: ID заявки.
            owner_id: ID владельца канала.
            final_price: Итоговая цена.
            final_schedule: Итоговое время публикации.

        Returns:
            Обновленная заявка.

        Raises:
            ValueError: Если проверки не пройдены.
        """
        from src.db.models.telegram_chat import TelegramChat

        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # Проверка: принадлежит каналу владельца
        channel = await self.session.get(TelegramChat, placement.channel_id)
        if not channel or channel.owner_id != owner_id:
            raise ValueError(CHANNEL_NOT_BELONG)

        # Проверка: статус pending_owner
        if placement.status != PlacementStatus.pending_owner:
            raise ValueError(f"Invalid status: {placement.status}")

        # Проверка: expires_at не истёк
        if placement.expires_at and placement.expires_at < datetime.now(UTC):
            raise ValueError("Placement expired")

        # Принимаем
        result = await self.placement_repo.accept(
            placement_id=placement_id,
            final_price=final_price,
            final_schedule=final_schedule,
        )

        # Отправляем уведомление рекламодателю
        advertiser = await self.session.get(User, placement.advertiser_id)
        if advertiser and result:
            await _notify_owner_accept(result, advertiser, channel)

        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)
        return result

    async def owner_reject(
        self,
        placement_id: int,
        owner_id: int,
        rejection_reason: str,
    ) -> PlacementRequest:
        """
        Владелец отклонил заявку.

        Проверки:
        1. rejection_reason валиден: len >= 10, содержит буквы, не 'asdfgh'/'12345'
        2. Статус == pending_owner

        Если rejection_reason невалиден:
        - Применить штраф репутации
        - Поднять ValueError с описанием

        Args:
            placement_id: ID заявки.
            owner_id: ID владельца канала.
            rejection_reason: Причина отклонения.

        Returns:
            Обновленная заявка.

        Raises:
            ValueError: Если reason невалиден или статус неверный.
        """
        from src.db.models.telegram_chat import TelegramChat

        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # Проверка: принадлежит каналу владельца
        channel = await self.session.get(TelegramChat, placement.channel_id)
        if not channel or channel.owner_id != owner_id:
            raise ValueError(CHANNEL_NOT_BELONG)

        # Проверка: статус pending_owner
        if placement.status != PlacementStatus.pending_owner:
            raise ValueError(f"Invalid status: {placement.status}")

        # Валидация reason
        if not self.validate_rejection_reason(rejection_reason):
            # Штраф репутации
            from src.core.services.reputation_service import ReputationService

            rep_service = ReputationService(self.session, self.reputation_repo)
            await rep_service.on_invalid_rejection(
                owner_id=owner_id,
                placement_request_id=placement_id,
            )
            raise ValueError("Invalid rejection reason")

        # Отклоняем
        result = await self.placement_repo.reject(
            placement_id=placement_id,
            rejection_reason=rejection_reason,
        )

        # Отправляем уведомление рекламодателю
        advertiser = await self.session.get(User, placement.advertiser_id)
        if advertiser and result:
            await _notify_rejected(result, advertiser, channel)

        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)
        return result

    async def owner_counter_offer(
        self,
        placement_id: int,
        owner_id: int,
        proposed_price: Decimal | None = None,
        proposed_schedule: datetime | None = None,
    ) -> PlacementRequest:
        """
        Владелец сделал контр-предложение.

        Проверки:
        1. counter_offer_count < 3 (не исчерпан лимит)
        2. Статус == pending_owner

        Args:
            placement_id: ID заявки.
            owner_id: ID владельца канала.
            proposed_price: Новая цена.
            proposed_schedule: Новое время публикации.

        Returns:
            Обновленная заявка.

        Raises:
            ValueError: Если лимит исчерпан или статус неверный.
        """
        from src.db.models.telegram_chat import TelegramChat

        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # Проверка: принадлежит каналу владельца
        channel = await self.session.get(TelegramChat, placement.channel_id)
        if not channel or channel.owner_id != owner_id:
            raise ValueError(CHANNEL_NOT_BELONG)

        # Проверка: статус pending_owner
        if placement.status != PlacementStatus.pending_owner:
            raise ValueError(f"Invalid status: {placement.status}")

        # Проверка: лимит не исчерпан
        if placement.counter_offer_count >= 3:
            raise ValueError("Counter offer limit reached")

        if proposed_price is None:
            raise ValueError("proposed_price is required for counter offer")

        # Контр-предложение
        result = await self.placement_repo.counter_offer(
            placement_id=placement_id,
            proposed_price=proposed_price,
            proposed_schedule=proposed_schedule,
        )

        if result is None:
            raise ValueError("Counter offer limit reached")

        # Устанавливаем срок действия контр-предложения (3 часа)
        from datetime import UTC, timedelta

        result.expires_at = datetime.now(UTC) + timedelta(hours=3)
        await self.session.flush()
        await self.session.refresh(result)

        # Отправляем уведомление рекламодателю
        advertiser = await self.session.get(User, placement.advertiser_id)
        if advertiser:
            await _notify_counter_offer(result, advertiser, channel)

        return result

    async def advertiser_accept_counter(
        self,
        placement_id: int,
        advertiser_id: int,
    ) -> PlacementRequest:
        """
        Рекламодатель принял контр-предложение.
        Статус → pending_payment.

        Args:
            placement_id: ID заявки.
            advertiser_id: ID рекламодателя.

        Returns:
            Обновленная заявка.

        Raises:
            ValueError: Если заявка не принадлежит advertiser или статус неверный.
        """
        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)

        if placement.advertiser_id != advertiser_id:
            raise ValueError(PLACEMENT_NOT_BELONG)

        if placement.status != PlacementStatus.counter_offer:
            raise ValueError(f"Invalid status: {placement.status}")

        # Принимаем контр-предложение → pending_payment
        result = await self.placement_repo.accept(placement_id=placement_id)

        # Отправляем уведомление владельцу
        channel = await self.session.get(TelegramChat, placement.channel_id)
        owner = await self.session.get(User, placement.channel.owner_id if placement.channel else 0)
        advertiser = await self.session.get(User, advertiser_id)
        if owner and advertiser and result and channel:
            await _notify_counter_accepted(result, advertiser, owner, channel)

        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)
        return result

    async def _refund_escrow_if_needed(
        self,
        placement: PlacementRequest,
        placement_id: int,
        advertiser_id: int,
    ) -> None:
        """Refund escrow when a billing transaction exists."""
        if not placement.escrow_transaction_id or not self.billing_service:
            return
        final_price = placement.final_price or placement.proposed_price
        owner_id = (placement.channel.owner_id if placement.channel else 0) or 0
        await self.billing_service.refund_escrow(
            session=self.session,
            placement_id=placement_id,
            final_price=final_price,
            advertiser_id=advertiser_id,
            owner_id=owner_id,
            scenario="after_escrow_before_confirmation",
        )

    async def _apply_systematic_cancellation_penalty(
        self,
        rep_service: Any,
        advertiser_id: int,
        placement_id: int,
    ) -> None:
        """Apply extra reputation penalty if advertiser has 3+ cancellations in 30 days."""
        cancellations = await self.placement_repo.count_cancellations_in_30_days(advertiser_id)
        if cancellations < 3:
            return
        from src.db.models.reputation_history import ReputationAction

        await rep_service._apply_delta(
            user_id=advertiser_id,
            role="advertiser",
            delta=rep_service.DELTA_CANCEL_SYSTEMATIC,
            action=ReputationAction.cancel_systematic,
            placement_request_id=placement_id,
            comment="Systematic cancellations (3+ in 30 days)",
        )

    async def advertiser_cancel(
        self,
        placement_id: int,
        advertiser_id: int,
    ) -> PlacementRequest:
        """
        Рекламодатель отменил заявку.

        Логика штрафов:
        - Статус == pending_owner → refund 100%, reputation delta = -5
        - Статус == pending_payment → refund 100%, reputation delta = -5
        - Статус == escrow → refund 50%, reputation delta = -20

        Проверить: если 3 отмены за 30 дней → ещё -20 + предупреждение

        Args:
            placement_id: ID заявки.
            advertiser_id: ID рекламодателя.

        Returns:
            Обновленная заявка.

        Raises:
            ValueError: Если заявка не принадлежит advertiser.
        """
        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)
        if placement.advertiser_id != advertiser_id:
            raise ValueError(PLACEMENT_NOT_BELONG)

        # Возврат средств через billing_service
        await self._refund_escrow_if_needed(placement, placement_id, advertiser_id)

        # Штраф репутации
        from src.core.services.reputation_service import ReputationService

        rep_service = ReputationService(self.session, self.reputation_repo)
        await rep_service.on_advertiser_cancel(
            advertiser_id=advertiser_id,
            placement_request_id=placement_id,
            after_confirmation=(placement.status != PlacementStatus.pending_owner),
        )
        await self._apply_systematic_cancellation_penalty(rep_service, advertiser_id, placement_id)

        # Отменяем заявку
        result = await self.placement_repo.reject(
            placement_id=placement_id,
            rejection_reason="Cancelled by advertiser",
        )

        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # Отправляем уведомление
        channel = await self.session.get(TelegramChat, placement.channel_id)
        owner = await self.session.get(User, placement.channel.owner_id if placement.channel else 0)
        advertiser = await self.session.get(User, advertiser_id)
        if owner and advertiser and channel:
            await _notify_cancelled(result, advertiser, owner, channel, 0.0)

        return result

    async def _freeze_escrow_for_payment(
        self,
        placement: PlacementRequest,
        placement_id: int,
        advertiser_id: int,
    ) -> PlacementRequest | None:
        """Move placement into escrow, handling test and real-payment paths."""
        if placement.is_test:
            result = await self.placement_repo.set_escrow(
                placement_id=placement_id,
                escrow_transaction_id=None,
            )
        else:
            if not self.billing_service:
                raise RuntimeError("BillingService not initialized")
            transaction = await self.billing_service.freeze_escrow_for_placement(
                session=self.session,
                placement_id=placement_id,
                advertiser_id=advertiser_id,
                amount=placement.final_price or placement.proposed_price,
            )
            result = await self.placement_repo.set_escrow(
                placement_id=placement_id,
                escrow_transaction_id=transaction.id,
            )

        # Ensure tracking_short_code exists before publication
        if result and not result.tracking_short_code:
            import secrets

            result.tracking_short_code = secrets.token_urlsafe(8)[:8]
            await self.session.flush()
            await self.session.refresh(result)  # reload expired updated_at after flush

        return result

    @staticmethod
    def _schedule_publication_task(result: PlacementRequest) -> None:
        """Enqueue a Celery task to publish the placement at the scheduled time."""
        from datetime import timedelta

        from src.tasks.placement_tasks import schedule_placement_publication

        scheduled = result.final_schedule or result.proposed_schedule
        if scheduled:
            scheduled_iso = scheduled.isoformat()
        else:
            scheduled_iso = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
        schedule_placement_publication.delay(result.id, scheduled_iso)

    async def process_payment(
        self,
        placement_id: int,
        advertiser_id: int,
    ) -> PlacementRequest:
        """
        Рекламодатель оплатил.
        Статус: pending_payment → escrow.

        Args:
            placement_id: ID заявки.
            advertiser_id: ID рекламодателя.

        Returns:
            Обновленная заявка.

        Raises:
            ValueError: Если заявка не принадлежит advertiser или статус неверный.
        """
        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)
        if placement.advertiser_id != advertiser_id:
            raise ValueError(PLACEMENT_NOT_BELONG)
        if placement.status != PlacementStatus.pending_payment:
            raise ValueError(f"Invalid status: {placement.status}")

        result = await self._freeze_escrow_for_payment(placement, placement_id, advertiser_id)

        if result:
            self._schedule_publication_task(result)

        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # Отправляем уведомления
        channel = await self.session.get(TelegramChat, placement.channel_id)
        owner = await self.session.get(User, placement.channel.owner_id if placement.channel else 0)
        advertiser = await self.session.get(User, advertiser_id)
        if owner and advertiser and channel:
            await _notify_payment_received(result, advertiser, owner, channel)

        return result

    async def process_publication_success(
        self,
        placement_id: int,
        published_at: datetime | None = None,
    ) -> PlacementRequest:
        """
        DEPRECATED v4.2: Публикация успешна.
        Эскроу освобождается ТОЛЬКО в publication_service.delete_published_post() (ESCROW-001).
        Этот метод больше не освобождает эскроу — только обновляет статус.

        Args:
            placement_id: ID заявки.
            published_at: Время публикации.

        Returns:
            Обновленная заявка.
        """
        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # v4.2: Эскроу НЕ освобождаем здесь — только в delete_published_post()
        # Репутация +1 за публикацию
        from src.core.services.reputation_service import ReputationService

        rep_service = ReputationService(self.session, self.reputation_repo)
        await rep_service.on_publication(
            advertiser_id=placement.advertiser_id,
            owner_id=(placement.channel.owner_id if placement.channel else 0) or 0,
            placement_request_id=placement_id,
        )

        # Обновляем статус
        result = await self.placement_repo.set_published(
            placement_id=placement_id,
            published_at=published_at,
        )

        # Уведомления отправляются в placement_tasks.py

        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)
        return result

    async def process_publication_failure(
        self,
        placement_id: int,
        reason: str,
    ) -> PlacementRequest:
        """
        Ошибка публикации (бот удалён, канал заблокирован).
        Статус → failed → refunded. Возврат 100%, репутация без изменений.

        Args:
            placement_id: ID заявки.
            reason: Причина ошибки.

        Returns:
            Обновленная заявка.
        """
        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # Возврат 100%
        if placement.escrow_transaction_id and self.billing_service:
            final_price = placement.final_price or placement.proposed_price
            owner_id = (placement.channel.owner_id if placement.channel else 0) or 0
            await self.billing_service.refund_escrow(
                session=self.session,
                placement_id=placement_id,
                final_price=final_price,
                advertiser_id=placement.advertiser_id,
                owner_id=owner_id,
                scenario="after_confirmation",
            )

        # Статус failed
        await self.placement_repo.update_status(
            placement_id=placement_id,
            new_status=PlacementStatus.failed,
        )

        # Статус refunded
        result = await self.placement_repo.update_status(
            placement_id=placement_id,
            new_status=PlacementStatus.refunded,
        )
        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)
        return result

    async def auto_expire(self, placement_id: int) -> PlacementRequest:
        """
        Авто-отклонение по истечении 24ч.
        Вызывается Celery-задачей.
        Статус → cancelled. Возврат 100%.

        Args:
            placement_id: ID заявки.

        Returns:
            Обновленная заявка.
        """
        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError(PLACEMENT_NOT_FOUND)

        # Возврат 100%
        if placement.escrow_transaction_id and self.billing_service:
            final_price = placement.final_price or placement.proposed_price
            owner_id = (placement.channel.owner_id if placement.channel else 0) or 0
            await self.billing_service.refund_escrow(
                session=self.session,
                placement_id=placement_id,
                final_price=final_price,
                advertiser_id=placement.advertiser_id,
                owner_id=owner_id,
                scenario="after_confirmation",
            )

        # Отменяем
        result = await self.placement_repo.reject(
            placement_id=placement_id,
            rejection_reason="Expired",
        )
        if result is None:
            raise ValueError(PLACEMENT_NOT_FOUND)
        return result

    def validate_rejection_reason(self, reason: str) -> bool:
        """
        Валидация комментария при отклонении:
        - len >= 10
        - содержит буквы (re.search(r'[а-яёa-z]', reason, re.I))
        - не является бессмысленным ('asdfgh', 'aaaaaa', '123456' и т.п.)

        Args:
            reason: Текст комментария.

        Returns:
            True если валиден.
        """
        if len(reason) < 10:
            return False

        # Проверка на наличие букв
        if not re.search(r"[а-яёa-z]", reason, re.IGNORECASE):
            return False

        # Проверка на бессмысленные комбинации
        meaningless_patterns = [
            r"^(asdf|asdfgh|aaaaaa|bbbbbb|123456|111111|qwerty)+$",
            r"^([a-z])\1{4,}$",  # 5+ одинаковых символов
            r"^([0-9])\1{4,}$",  # 5+ одинаковых цифр
        ]

        return all(not re.match(pattern, reason, re.IGNORECASE) for pattern in meaningless_patterns)

    # ══════════════════════════════════════════════════════════════
    # S-08: PlacementRequestService v4.2 — новые методы
    # ══════════════════════════════════════════════════════════════

    async def create_placement_request(
        self,
        session: AsyncSession,
        advertiser_id: int,
        channel_id: int,
        publication_format: str,
        ad_text: str,
        proposed_price: Decimal | None = None,
    ) -> PlacementRequest:
        """
        Создать заявку на размещение v4.2.

        Порядок проверок:
        1. channel exists
        2. self-dealing (channel.owner_id == advertiser_id)
        3. plan format limit
        4. channel allows format
        5. price calculation
        6. MIN_CAMPAIGN_BUDGET
        7. create

        Args:
            session: Асинхронная сессия.
            advertiser_id: ID рекламодателя.
            channel_id: ID канала.
            publication_format: Формат публикации (post_24h/post_48h/post_7d/pin_24h/pin_48h).
            ad_text: Текст рекламы.
            proposed_price: Предлагаемая цена (опционально).

        Returns:
            Созданная заявка.

        Raises:
            SelfDealingError: Если advertiser == channel.owner.
            PlanLimitError: Если формат недоступен на тарифе.
            ValueError: Если канал не принимает формат или цена < MIN_CAMPAIGN_BUDGET.
        """

        from src.constants.payments import (
            FORMAT_MULTIPLIERS,
            MIN_CAMPAIGN_BUDGET,
            MIN_PRICE_PER_POST,
            PLAN_LIMITS,
        )
        from src.db.models.telegram_chat import TelegramChat
        from src.db.models.user import User

        # 1. Получить канал
        channel = await session.get(TelegramChat, channel_id)
        if channel is None:
            raise ValueError("Канал не найден")

        # 2. ПЕРВАЯ проверка — self-dealing (до любых запросов в БД кроме channel)
        if channel.owner_id == advertiser_id:
            from src.core.exceptions import SelfDealingError

            raise SelfDealingError("Нельзя размещать рекламу на собственном канале")

        # 3. Получить рекламодателя
        advertiser = await session.get(User, advertiser_id)
        if not advertiser:
            raise ValueError("Рекламодатель не найден")

        # 3. Проверить формат по тарифу
        allowed_formats = PLAN_LIMITS.get(advertiser.plan, {}).get("formats", [])
        if publication_format not in allowed_formats:
            from src.core.exceptions import PlanLimitError

            raise PlanLimitError(
                f"Формат {publication_format} недоступен на тарифе {advertiser.plan}"
            )

        # 4. Получить настройки канала
        channel_settings = await self.channel_settings_repo.get_by_channel(channel_id)
        if not channel_settings:
            raise ValueError(f"Настройки канала {channel_id} не найдены")

        allow_field = f"allow_format_{publication_format}"
        if not getattr(channel_settings, allow_field, False):
            raise ValueError(f"Владелец канала не принимает формат {publication_format}")

        # 5. Расчёт цены
        base_price = channel_settings.price_per_post
        if base_price < MIN_PRICE_PER_POST:
            raise ValueError(f"Цена поста не может быть меньше {MIN_PRICE_PER_POST} ₽")

        multiplier = FORMAT_MULTIPLIERS.get(publication_format)
        if multiplier is None:
            raise ValueError(f"Неизвестный формат: {publication_format}")

        from decimal import ROUND_HALF_UP

        calculated_price = (base_price * multiplier).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 6. Проверка MIN_CAMPAIGN_BUDGET
        if calculated_price < MIN_CAMPAIGN_BUDGET:
            raise ValueError(
                f"Итоговая цена {calculated_price} ₽ меньше минимального бюджета {MIN_CAMPAIGN_BUDGET} ₽"
            )

        # 7. Создать PlacementRequest
        return await self.placement_repo.create_placement(
            advertiser_id=advertiser_id,
            campaign_id=None,
            channel_id=channel_id,
            proposed_price=calculated_price,
            final_text=ad_text,
            proposed_schedule=None,
            proposed_frequency=None,
        )

    def calculate_placement_price(
        self,
        base_price: Decimal,
        publication_format: str,
    ) -> Decimal:
        """
        Рассчитать цену размещения по формату.

        Args:
            base_price: Базовая цена поста.
            publication_format: Формат публикации.

        Returns:
            Цена с учётом формата.

        Raises:
            ValueError: Если неизвестный формат.
        """
        from src.constants.payments import FORMAT_MULTIPLIERS

        multiplier = FORMAT_MULTIPLIERS.get(publication_format)
        if multiplier is None:
            raise ValueError(f"Неизвестный формат: {publication_format}")

        from decimal import ROUND_HALF_UP

        return (base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Импортируем Any для type hint
