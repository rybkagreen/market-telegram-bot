"""
PlacementRequest Service — оркестратор всего флоу создания и исполнения заявки.
"""

import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.analytics import TelegramChat
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.user import User
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo

if TYPE_CHECKING:
    from src.core.services.billing_service import BillingService

logger = logging.getLogger(__name__)


# =============================================================================
# УВЕДОМЛЕНИЯ (импортируются здесь для избежания circular imports)
# =============================================================================


async def _notify_create_request(placement, advertiser, owner, channel):
    """Отправить уведомление о новой заявке."""
    try:
        from src.bot.handlers.shared.notifications import notify_new_request
        await notify_new_request(placement, advertiser, owner, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_owner_accept(placement, advertiser, channel):
    """Отправить уведомление о принятии заявки владельцем."""
    try:
        from src.bot.handlers.shared.notifications import notify_owner_accepted
        await notify_owner_accepted(placement, advertiser, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_counter_offer(placement, advertiser, channel):
    """Отправить уведомление о контр-предложении."""
    try:
        from src.bot.handlers.shared.notifications import notify_counter_offer
        await notify_counter_offer(placement, advertiser, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_counter_accepted(placement, advertiser, owner, channel):
    """Отправить уведомление о принятии контр-предложения."""
    try:
        from src.bot.handlers.shared.notifications import notify_counter_accepted
        await notify_counter_accepted(placement, advertiser, owner, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_payment_received(placement, advertiser, owner, channel):
    """Отправить уведомление о получении оплаты."""
    try:
        from src.bot.handlers.shared.notifications import notify_payment_received
        await notify_payment_received(placement, advertiser, owner, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_rejected(placement, advertiser, channel):
    """Отправить уведомление об отклонении заявки."""
    try:
        from src.bot.handlers.shared.notifications import notify_rejected
        await notify_rejected(placement, advertiser, channel.username or f"ID:{channel.id}")
    except Exception as e:
        logger.warning(f"Failed to send notification for placement {placement.id}: {e}")


async def _notify_cancelled(placement, advertiser, owner, channel, reputation_delta=0.0):
    """Отправить уведомление об отмене заявки."""
    try:
        from src.bot.handlers.shared.notifications import notify_cancelled
        await notify_cancelled(placement, advertiser, owner, channel.username or f"ID:{channel.id}", reputation_delta)
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
        placement_repo: PlacementRequestRepo,
        channel_settings_repo: ChannelSettingsRepo,
        reputation_repo: ReputationRepo,
        billing_service: "BillingService",
    ):
        """
        Инициализация сервиса.

        Args:
            session: Асинхронная сессия SQLAlchemy.
            placement_repo: Репозиторий заявок.
            channel_settings_repo: Репозиторий настроек каналов.
            reputation_repo: Репозиторий репутации.
            billing_service: Сервис платежей.
        """
        self.session = session
        self.placement_repo = placement_repo
        self.channel_settings_repo = channel_settings_repo
        self.reputation_repo = reputation_repo
        self.billing_service = billing_service

    async def create_request(
        self,
        advertiser_id: int,
        campaign_id: int,
        channel_id: int,
        proposed_price: Decimal,
        final_text: str,
        proposed_schedule: datetime | None = None,
        proposed_frequency: int | None = None,
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

        Returns:
            Созданная заявка.

        Raises:
            ValueError: Если проверки не пройдены.
        """
        from src.db.models.analytics import TelegramChat

        # Проверка 1: advertiser не заблокирован
        rep_score = await self.reputation_repo.get_by_user(advertiser_id)
        if rep_score and rep_score.is_advertiser_blocked:
            if rep_score.advertiser_blocked_until and rep_score.advertiser_blocked_until > datetime.now(UTC):
                raise ValueError("Advertiser is blocked")

        # Проверка 2: цена >= минимальной
        if proposed_price < PlacementRequest.MIN_PRICE_PER_POST:
            raise ValueError(f"Price must be >= {PlacementRequest.MIN_PRICE_PER_POST}")

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
        )

        # Отправляем уведомление владельцу
        owner = await self.session.get(User, channel.owner_user_id)
        advertiser = await self.session.get(User, advertiser_id)
        if owner and advertiser:
            await _notify_create_request(placement, advertiser, owner, channel)

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
        from src.db.models.analytics import TelegramChat

        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError("Placement not found")

        # Проверка: принадлежит каналу владельца
        channel = await self.session.get(TelegramChat, placement.channel_id)
        if not channel or channel.owner_user_id != owner_id:
            raise ValueError("Channel does not belong to owner")

        # Проверка: статус pending_owner
        if placement.status != PlacementStatus.PENDING_OWNER:
            raise ValueError(f"Invalid status: {placement.status}")

        # Проверка: expires_at не истёк
        if placement.expires_at < datetime.now(UTC):
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
        from src.db.models.analytics import TelegramChat

        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError("Placement not found")

        # Проверка: принадлежит каналу владельца
        channel = await self.session.get(TelegramChat, placement.channel_id)
        if not channel or channel.owner_user_id != owner_id:
            raise ValueError("Channel does not belong to owner")

        # Проверка: статус pending_owner
        if placement.status != PlacementStatus.PENDING_OWNER:
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
        from src.db.models.analytics import TelegramChat

        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError("Placement not found")

        # Проверка: принадлежит каналу владельца
        channel = await self.session.get(TelegramChat, placement.channel_id)
        if not channel or channel.owner_user_id != owner_id:
            raise ValueError("Channel does not belong to owner")

        # Проверка: статус pending_owner
        if placement.status != PlacementStatus.PENDING_OWNER:
            raise ValueError(f"Invalid status: {placement.status}")

        # Проверка: лимит не исчерпан
        if placement.counter_offer_count >= 3:
            raise ValueError("Counter offer limit reached")

        # Контр-предложение
        result = await self.placement_repo.counter_offer(
            placement_id=placement_id,
            proposed_price=proposed_price,
            proposed_schedule=proposed_schedule,
        )

        if result is None:
            raise ValueError("Counter offer limit reached")

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
            raise ValueError("Placement not found")

        if placement.advertiser_id != advertiser_id:
            raise ValueError("Placement does not belong to advertiser")

        if placement.status != PlacementStatus.COUNTER_OFFER:
            raise ValueError(f"Invalid status: {placement.status}")

        # Принимаем контр-предложение → pending_payment
        result = await self.placement_repo.accept(placement_id=placement_id)

        # Отправляем уведомление владельцу
        channel = await self.session.get(TelegramChat, placement.channel_id)
        owner = await self.session.get(User, placement.channel.owner_user_id if placement.channel else 0)
        advertiser = await self.session.get(User, advertiser_id)
        if owner and advertiser and result and channel:
            await _notify_counter_accepted(result, advertiser, owner, channel)

        return result

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
            raise ValueError("Placement not found")

        if placement.advertiser_id != advertiser_id:
            raise ValueError("Placement does not belong to advertiser")

        # Определяем штраф
        if placement.status in [PlacementStatus.PENDING_OWNER, PlacementStatus.PENDING_PAYMENT]:
            delta = -5.0
            refund_percentage = Decimal("1.0")  # 100%
        elif placement.status == PlacementStatus.ESCROW:
            delta = -20.0
            refund_percentage = Decimal("0.5")  # 50%
        else:
            delta = 0.0
            refund_percentage = Decimal("0.0")

        # Возврат средств через billing_service
        if placement.escrow_transaction_id:
            refund_amount = (placement.final_price or placement.proposed_price) * refund_percentage
            await self.billing_service.refund_escrow(
                placement_id=placement_id,
                advertiser_id=advertiser_id,
                amount=refund_amount,
            )

        # Штраф репутации
        from src.core.services.reputation_service import ReputationService
        rep_service = ReputationService(self.session, self.reputation_repo)
        await rep_service.on_advertiser_cancel(
            advertiser_id=advertiser_id,
            placement_request_id=placement_id,
            after_confirmation=(placement.status != PlacementStatus.PENDING_OWNER),
        )

        # Проверка на систематические отмены
        cancellations = await self.placement_repo.count_cancellations_in_30_days(advertiser_id)
        if cancellations >= 3:
            # Используем существующий метод с правильным названием
            from src.db.models.reputation_history import ReputationAction
            await rep_service._apply_delta(
                user_id=advertiser_id,
                role="advertiser",
                delta=rep_service.DELTA_CANCEL_SYSTEMATIC,
                action=ReputationAction.CANCEL_SYSTEMATIC,
                placement_request_id=placement_id,
                comment="Systematic cancellations (3+ in 30 days)",
            )

        # Отменяем заявку
        result = await self.placement_repo.reject(
            placement_id=placement_id,
            rejection_reason="Cancelled by advertiser",
        )

        # Отправляем уведомление
        channel = await self.session.get(TelegramChat, placement.channel_id)
        owner = await self.session.get(User, placement.channel.owner_user_id if placement.channel else 0)
        advertiser = await self.session.get(User, advertiser_id)
        if owner and advertiser and result and channel:
            await _notify_cancelled(result, advertiser, owner, channel, delta)

        return result

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
            raise ValueError("Placement not found")

        if placement.advertiser_id != advertiser_id:
            raise ValueError("Placement does not belong to advertiser")

        if placement.status != PlacementStatus.PENDING_PAYMENT:
            raise ValueError(f"Invalid status: {placement.status}")

        # Блокируем средства
        transaction = await self.billing_service.freeze_escrow_for_placement(
            placement_id=placement_id,
            advertiser_id=advertiser_id,
            amount=placement.final_price or placement.proposed_price,
        )

        # Обновляем статус
        result = await self.placement_repo.set_escrow(
            placement_id=placement_id,
            escrow_transaction_id=transaction.id,
        )

        # Отправляем уведомления
        channel = await self.session.get(TelegramChat, placement.channel_id)
        owner = await self.session.get(User, placement.channel.owner_user_id if placement.channel else 0)
        advertiser = await self.session.get(User, advertiser_id)
        if owner and advertiser and result and channel:
            await _notify_payment_received(result, advertiser, owner, channel)

        return result

    async def process_publication_success(
        self,
        placement_id: int,
        published_at: datetime | None = None,
    ) -> PlacementRequest:
        """
        Публикация успешна.
        Статус → published.

        Args:
            placement_id: ID заявки.
            published_at: Время публикации.

        Returns:
            Обновленная заявка.
        """
        placement = await self.placement_repo.get_by_id(placement_id)
        if not placement:
            raise ValueError("Placement not found")

        # Разблокируем средства (80% owner, 20% комиссия)
        owner_id = placement.channel.owner_user_id if placement.channel else None
        if not owner_id:
            logger.error(f"Channel not found for placement {placement_id}")
            return await self.placement_repo.get_by_id(placement_id)

        await self.billing_service.release_escrow_for_placement(
            placement_id=placement_id,
            owner_id=placement.channel.owner_user_id,
            total_amount=placement.final_price or placement.proposed_price,
        )

        # Репутация +1 за публикацию
        from src.core.services.reputation_service import ReputationService
        rep_service = ReputationService(self.session, self.reputation_repo)
        await rep_service.on_publication(
            advertiser_id=placement.advertiser_id,
            owner_id=owner_id,
            placement_request_id=placement_id,
        )

        # Обновляем статус
        result = await self.placement_repo.set_published(
            placement_id=placement_id,
            published_at=published_at,
        )

        # Отправляем уведомления (вызывается из Celery задачи)
        # Уведомления отправляются в placement_tasks.py

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
            raise ValueError("Placement not found")

        # Возврат 100%
        if placement.escrow_transaction_id:
            await self.billing_service.refund_escrow(
                placement_id=placement_id,
                advertiser_id=placement.advertiser_id,
                amount=placement.final_price or placement.proposed_price,
            )

        # Статус failed
        await self.placement_repo.update_status(
            placement_id=placement_id,
            status=PlacementStatus.FAILED,
        )

        # Статус refunded
        return await self.placement_repo.update_status(
            placement_id=placement_id,
            status=PlacementStatus.REFUNDED,
        )

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
            raise ValueError("Placement not found")

        # Возврат 100%
        if placement.escrow_transaction_id:
            await self.billing_service.refund_escrow(
                placement_id=placement_id,
                advertiser_id=placement.advertiser_id,
                amount=placement.final_price or placement.proposed_price,
            )

        # Отменяем
        return await self.placement_repo.reject(
            placement_id=placement_id,
            rejection_reason="Expired",
        )

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
        if not re.search(r'[а-яёa-z]', reason, re.IGNORECASE):
            return False

        # Проверка на бессмысленные комбинации
        meaningless_patterns = [
            r'^(asdf|asdfgh|aaaaaa|bbbbbb|123456|111111|qwerty)+$',
            r'^([a-z])\1{4,}$',  # 5+ одинаковых символов
            r'^([0-9])\1{4,}$',  # 5+ одинаковых цифр
        ]

        for pattern in meaningless_patterns:
            if re.match(pattern, reason, re.IGNORECASE):
                return False

        return True


# Импортируем Any для type hint
