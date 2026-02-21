"""
Репозитории для работы с базой данных.
Все репозитории импортируются здесь для удобства.
"""

from src.db.repositories.base import BaseRepository
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.chat_repo import ChatRepository, ChatData
from src.db.repositories.log_repo import MailingLogRepository, LogData
from src.db.repositories.user_repo import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "CampaignRepository",
    "ChatRepository",
    "ChatData",
    "MailingLogRepository",
    "LogData",
]
