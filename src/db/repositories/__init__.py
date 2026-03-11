"""
Репозитории для работы с базой данных.
Все репозитории импортируются здесь для удобства.
"""

from src.db.repositories.base import BaseRepository
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.repositories.log_repo import LogData, MailingLogRepository
from src.db.repositories.notification_repo import NotificationRepository
from src.db.repositories.user_repo import UserRepository

# Type aliases for backwards compatibility
UserRepo = UserRepository
CampaignRepo = CampaignRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "UserRepo",
    "CampaignRepository",
    "CampaignRepo",
    "MailingLogRepository",
    "LogData",
    "ChatAnalyticsRepository",
    "NotificationRepository",
]

# Новые репозитории (Этап 2)
from src.db.repositories.channel_settings_repo import ChannelSettingsRepo
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.repositories.reputation_repo import ReputationRepo

__all__.extend([
    "PlacementRequestRepo",
    "ChannelSettingsRepo",
    "ReputationRepo",
])
