"""
Модели SQLAlchemy для базы данных.
Все модели импортируются здесь для удобства и для Alembic.
"""

from src.db.models.analytics import ChatSnapshot, ChatType, TelegramChat
from src.db.models.b2b_package import B2BPackage
from src.db.models.badge import Badge, UserBadge
from src.db.models.campaign import Campaign, CampaignStatus
from src.db.models.channel_mediakit import ChannelMediakit
from src.db.models.channel_rating import ChannelRating
from src.db.models.content_flag import ContentFlag, ContentFlagCategory, ContentFlagDecision
from src.db.models.crypto_payment import CryptoPayment, PaymentMethod, PaymentStatus
from src.db.models.mailing_log import MailingLog, MailingStatus
from src.db.models.notification import Notification, NotificationType
from src.db.models.payout import Payout, PayoutCurrency, PayoutStatus
from src.db.models.review import Review, ReviewerRole
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User, UserPlan

# Экспорт всех моделей для Alembic
__all__ = [
    "User",
    "UserPlan",
    "Campaign",
    "CampaignStatus",
    "MailingLog",
    "MailingStatus",
    "Transaction",
    "TransactionType",
    "ContentFlag",
    "ContentFlagCategory",
    "ContentFlagDecision",
    "TelegramChat",
    "ChatSnapshot",
    "ChatType",
    "Notification",
    "NotificationType",
    "CryptoPayment",
    "PaymentMethod",
    "PaymentStatus",
    "Payout",
    "PayoutStatus",
    "PayoutCurrency",
    "Review",
    "ReviewerRole",
    "ChannelRating",
    "ChannelMediakit",
    "Badge",
    "UserBadge",
    "B2BPackage",
]
