"""
UserService — бизнес-логика для работы с пользователями.
Handlers вызывают методы сервиса и не знают о БД.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository


@dataclass
class CabinetData:
    """Данные для экрана личного кабинета."""

    balance: Decimal
    plan: str
    total_campaigns: int
    active_campaigns: int
    created_at: str
    referral_code: str


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._user_repo = UserRepository(session)
        self._campaign_repo = CampaignRepository(session)

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None = None,
        language_code: str | None = None,
    ):
        """Получить или создать пользователя. Возвращает (user, is_new)."""
        user = await self._user_repo.create_or_update(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        # Проверяем, новый ли пользователь (только что создан)
        is_new = user.created_at == user.updated_at
        return user, is_new

    async def get_cabinet_data(self, telegram_id: int) -> CabinetData:
        """Собрать все данные для экрана кабинета одним вызовом."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        total = await self._campaign_repo.get_user_campaigns_count(user.id)
        active = await self._campaign_repo.get_user_campaigns_count(user.id, status="running")

        plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan

        return CabinetData(
            balance=user.balance,
            plan=plan_value,
            total_campaigns=total,
            active_campaigns=active,
            created_at=user.created_at.strftime("%d.%m.%Y"),
            referral_code=user.referral_code or str(user.telegram_id),
        )

    async def get_campaigns_page(self, telegram_id: int, page: int = 1, per_page: int = 5):
        """Кампании пользователя с пагинацией."""
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        return await self._campaign_repo.get_by_user(
            user_id=user.id,
            page=page,
            page_size=per_page,
        )
