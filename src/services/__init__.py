"""
Фабрики сервисов — создают сервис с сессией для использования в handlers.

Использование в handler:
    from src.services import get_user_service

    async with get_user_service() as svc:
        data = await svc.get_cabinet_data(user.id)
"""

from contextlib import asynccontextmanager

from src.db.session import async_session_factory
from src.services.billing_service import BillingService
from src.services.campaign_service import CampaignService
from src.services.user_service import UserService


@asynccontextmanager
async def get_user_service():
    """Фабрика UserService."""
    async with async_session_factory() as session:
        yield UserService(session)


@asynccontextmanager
async def get_billing_service():
    """Фабрика BillingService."""
    async with async_session_factory() as session:
        yield BillingService(session)


@asynccontextmanager
async def get_campaign_service():
    """Фабрика CampaignService."""
    async with async_session_factory() as session:
        yield CampaignService(session)
