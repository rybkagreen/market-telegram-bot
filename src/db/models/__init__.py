"""
Модели SQLAlchemy для базы данных.
Все модели импортируются здесь для удобства и для Alembic.
"""

from src.db.models.campaign import Campaign, CampaignStatus
from src.db.models.chat import Chat
from src.db.models.content_flag import ContentFlag, ContentFlagCategory, ContentFlagDecision
from src.db.models.mailing_log import MailingLog, MailingStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User, UserPlan

# Экспорт всех моделей для Alembic
__all__ = [
    "User",
    "UserPlan",
    "Campaign",
    "CampaignStatus",
    "Chat",
    "MailingLog",
    "MailingStatus",
    "Transaction",
    "TransactionType",
    "ContentFlag",
    "ContentFlagCategory",
    "ContentFlagDecision",
]
