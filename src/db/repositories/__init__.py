# src/db/repositories/__init__.py
from src.db.repositories.badge_repo import BadgeRepository
from src.db.repositories.base import BaseRepository
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.click_tracking_repo import ClickTrackingRepository
from src.db.repositories.dispute_repo import DisputeRepository
from src.db.repositories.document_upload_repo import DocumentUploadRepository
from src.db.repositories.kudir_repo import KudirRecordRepository
from src.db.repositories.mailing_log_repo import MailingLogRepository
from src.db.repositories.payout_repo import PayoutRepository
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.platform_account_repo import PlatformAccountRepository
from src.db.repositories.platform_revenue_repo import PlatformQuarterlyRevenueRepository
from src.db.repositories.telegram_chat_repo import TelegramChatRepository
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.repositories.yookassa_payment_repo import YookassaPaymentRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "TelegramChatRepository",
    "PlacementRequestRepository",
    "TransactionRepository",
    "PayoutRepository",
    "PlatformAccountRepository",
    "DisputeRepository",
    # D-14: New repositories
    "CampaignRepository",
    "BadgeRepository",
    "YookassaPaymentRepository",
    "ClickTrackingRepository",
    "KudirRecordRepository",
    "DocumentUploadRepository",
    "MailingLogRepository",
    "PlatformQuarterlyRevenueRepository",
]
