"""
CampaignService — бизнес-логика для создания и управления кампаниями.
Handlers вызывают методы сервиса и не знают о БД.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.ai_service import AIService
from src.db.models.campaign import CampaignStatus
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.utils.content_filter.filter import check as content_filter_check


@dataclass
class CampaignCreateData:
    """Данные для создания кампании."""

    title: str
    text: str
    topic: str
    header: str | None = None
    image_file_id: str | None = None
    member_count_range: str = "any"
    scheduled_at: datetime | None = None
    is_free: bool = False  # для админа


@dataclass
class CampaignValidationResult:
    """Результат валидации кампании."""

    success: bool
    error: str | None = None
    campaign_id: int | None = None
    flagged_categories: list[str] | None = None


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaign_repo = CampaignRepository(session)
        self._user_repo = UserRepository(session)
        self._ai_service = AIService()

    async def validate_content(self, text: str) -> CampaignValidationResult:
        """
        Проверить текст кампании контент-фильтром.

        Args:
            text: Текст кампании.

        Returns:
            Результат валидации.
        """
        filter_result = await content_filter_check(text)

        if filter_result.is_blocked:
            return CampaignValidationResult(
                success=False,
                error=f"Контент заблокирован: {', '.join(filter_result.blocked_categories)}",
                flagged_categories=filter_result.blocked_categories,
            )

        return CampaignValidationResult(success=True)

    async def save_draft(self, telegram_id: int, data: CampaignCreateData) -> int:
        """
        Сохранить черновик кампании без запуска.

        Args:
            telegram_id: Telegram ID пользователя.
            data: Данные кампании.

        Returns:
            ID сохранённой кампании.
        """
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        campaign = await self._campaign_repo.create(
            user_id=user.id,
            title=data.title,
            text=data.text,
            topic=data.topic,
            header=data.header,
            image_file_id=data.image_file_id,
            status=CampaignStatus.DRAFT,
            scheduled_at=data.scheduled_at,
        )

        return campaign.id

    async def create_and_launch(
        self,
        telegram_id: int,
        data: CampaignCreateData,
    ) -> CampaignValidationResult:
        """
        Проверить контент, списать баланс, создать и запустить кампанию.

        Args:
            telegram_id: Telegram ID пользователя.
            data: Данные кампании.

        Returns:
            Результат создания кампании.
        """
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        # Проверяем контент
        validation = await self.validate_content(data.text)
        if not validation.success:
            return validation

        # Рассчитываем стоимость (заглушка — в production реальная логика)
        cost = Decimal("100")  # 100₽ за кампанию

        # Проверяем баланс
        if not data.is_free and user.balance < cost:
            return CampaignValidationResult(
                success=False,
                error=f"Недостаточно средств. Требуется: {cost}₽, баланс: {user.balance}₽",
            )

        # Создаём кампанию
        campaign = await self._campaign_repo.create(
            user_id=user.id,
            title=data.title,
            text=data.text,
            topic=data.topic,
            header=data.header,
            image_file_id=data.image_file_id,
            status=CampaignStatus.QUEUED if data.scheduled_at else CampaignStatus.RUNNING,
            scheduled_at=data.scheduled_at,
            cost=cost,
        )

        # Списываем баланс (если не бесплатно)
        if not data.is_free:
            await self._user_repo.update_balance(user.id, -cost)

        # Запускаем рассылку (если не запланирована)
        if not data.scheduled_at:
            from src.tasks.mailing_tasks import send_campaign

            send_campaign.delay(campaign.id)

        return CampaignValidationResult(
            success=True,
            campaign_id=campaign.id,
        )

    async def get_campaign_stats(self, campaign_id: int) -> dict | None:
        """
        Получить статистику кампании.

        Args:
            campaign_id: ID кампании.

        Returns:
            Статистика или None.
        """
        campaign = await self._campaign_repo.get_with_stats(campaign_id)
        if not campaign:
            return None

        return {
            "id": campaign.id,
            "title": campaign.title,
            "status": campaign.status.value,
            "total_chats": campaign.total_chats,
            "sent_count": campaign.sent_count,
            "failed_count": campaign.failed_count,
            "skipped_count": campaign.skipped_count,
            "progress": campaign.progress,
            "success_rate": campaign.success_rate,
        }
