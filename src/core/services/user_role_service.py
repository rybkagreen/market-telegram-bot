"""
Сервис динамического определения роли пользователя.

Роль определяется из БД — не хранится как поле User.
Один пользователь может быть одновременно рекламодателем и владельцем канала.
"""

from dataclasses import dataclass
from enum import Enum

from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.log_repo import MailingLogRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory


class UserRole(str, Enum):
    """Роль пользователя в системе."""

    NEW = "new"  # нет ни каналов, ни кампаний
    ADVERTISER = "advertiser"  # есть кампании, нет своих каналов
    OWNER = "owner"  # есть каналы, нет кампаний
    BOTH = "both"  # есть и то и другое


@dataclass
class UserContext:
    """Контекст пользователя для построения меню."""

    role: UserRole
    pending_requests_count: int  # непрочитанные заявки для владельца
    credits: int  # баланс для отображения в кнопке
    has_channels: bool  # флаг наличия каналов
    has_campaigns: bool  # флаг наличия кампаний


class UserRoleService:
    """
    Сервис определения роли пользователя на основе данных из БД.

    Роль определяется динамически при каждом запросе — не кешируется,
    чтобы меню всегда отражало актуальное состояние.
    """

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self._session_factory = async_session_factory

    async def get_user_context(self, user_db_id: int) -> UserContext:
        """
        Определить роль и контекст пользователя для построения меню.

        Вызывается при каждом показе главного меню.

        Args:
            user_db_id: ID пользователя в БД (не telegram_id).

        Returns:
            UserContext с ролью и контекстом.
        """
        async with self._session_factory() as session:
            user_repo = UserRepository(session)
            campaign_repo = CampaignRepository(session)
            mailing_log_repo = MailingLogRepository(session)

            # 1. Проверка наличия каналов (Спринт 0)
            has_channels = await user_repo.has_channels(user_db_id)

            # 2. Проверка наличия кампаний
            has_campaigns = await campaign_repo.has_campaigns(user_db_id)

            # 3. Счётчик ожидающих заявок (только если есть каналы)
            pending_count = 0
            if has_channels:
                pending_count = await mailing_log_repo.count_pending_for_owner(user_db_id)

            # 4. Баланс
            user = await user_repo.get_by_id(user_db_id)
            credits = user.credits if user else 0

            # Определить роль
            if has_channels and has_campaigns:
                role = UserRole.BOTH
            elif has_channels:
                role = UserRole.OWNER
            elif has_campaigns:
                role = UserRole.ADVERTISER
            else:
                role = UserRole.NEW

            return UserContext(
                role=role,
                pending_requests_count=pending_count,
                credits=credits,
                has_channels=has_channels,
                has_campaigns=has_campaigns,
            )

    async def get_role(self, user_db_id: int) -> UserRole:
        """
        Получить только роль пользователя (без контекста).

        Args:
            user_db_id: ID пользователя в БД.

        Returns:
            UserRole пользователя.
        """
        ctx = await self.get_user_context(user_db_id)
        return ctx.role
