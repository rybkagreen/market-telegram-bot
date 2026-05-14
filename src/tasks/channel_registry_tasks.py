"""Channel blogger-registry periodic re-verification tasks (BL-107 Phase B.6).

Daily Celery Beat task that re-verifies every channel which is currently
subject к ФЗ-303 (member_count >= rkn_threshold_subscribers, не is_test,
is_active). For each channel:

1. Refresh `member_count` via Telegram API.
2. Update `last_blogger_registry_check_at`.
3. Detect threshold crossings (channel grew past 10k since verification).
4. For channels verified via `TRUSTCHANNELBOT_ADMIN` method — re-run
   `verify_trustchannelbot_admin`. If Trustchannelbot is no longer
   admin → reset verification fields, write audit log, notify owner.

`MANUAL_EVIDENCE` channels are explicitly NOT re-checked — admin
decisions stand until owner submits new evidence or admin revokes
through a future flow (out of scope BL-107).

S-48 compliance: this module is the top-level caller for its own
unit of work — `session.commit()` is allowed inside the task body.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from src.config.settings import settings
from src.core.enums.blogger_registry import BloggerRegistryVerificationMethod
from src.core.services.notification_service import notify_owner_verification_lost
from src.db.models.telegram_chat import TelegramChat
from src.db.repositories.audit_log_repo import AuditLogRepo
from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks._bot_factory import ephemeral_bot
from src.tasks.celery_app import celery_app
from src.utils.telegram.verify_blogger_registry import (
    TrustchannelbotResolutionError,
    verify_trustchannelbot_admin,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="parser:check_channel_registry_status", queue="parser")
def check_channel_registry_status() -> dict[str, Any]:
    """Periodic re-verification of channels under ФЗ-303 (BL-107 Phase B.6).

    Iterates channels с `member_count >= rkn_threshold_subscribers AND
    NOT is_test AND is_active`. Refreshes member_count, re-checks
    Trustchannelbot admin status (only for TRUSTCHANNELBOT_ADMIN method),
    detects threshold crossings, updates audit timestamps, enqueues owner
    notifications on verification loss.

    Returns counters dict для observability / tests.
    """
    return asyncio.run(_check_channel_registry_status_async())


async def _check_channel_registry_status_async() -> dict[str, Any]:
    """Async implementation of the periodic re-verification task."""
    if not settings.rkn_periodic_check_enabled:
        logger.info("BL-107 periodic check skipped: rkn_periodic_check_enabled=False")
        return {"skipped": "disabled"}

    counters: dict[str, Any] = {
        "processed": 0,
        "threshold_crossed": 0,
        "verification_lost": 0,
        "still_verified": 0,
        "member_count_refreshed": 0,
        "api_failures": 0,
    }

    async with ephemeral_bot() as bot, async_session_factory() as session:
        stmt = select(TelegramChat).where(
            TelegramChat.member_count >= settings.rkn_threshold_subscribers,
            TelegramChat.is_test == False,  # noqa: E712
            TelegramChat.is_active == True,  # noqa: E712
        )
        result = await session.execute(stmt)
        channels = list(result.scalars().all())

        audit = AuditLogRepo(session)

        for channel in channels:
            counters["processed"] += 1
            now = datetime.now(UTC)

            try:
                chat = await bot.get_chat(channel.telegram_id)
                new_member_count = (
                    await chat.get_member_count() if hasattr(chat, "get_member_count") else 0
                )

                if (
                    channel.member_count_at_verification is not None
                    and channel.member_count_at_verification < settings.rkn_threshold_subscribers
                    and new_member_count >= settings.rkn_threshold_subscribers
                ):
                    counters["threshold_crossed"] += 1
                    logger.warning(
                        "BL-107: channel %s crossed ФЗ-303 threshold since verification "
                        "(was=%s, now=%s) — admin should re-review",
                        channel.id,
                        channel.member_count_at_verification,
                        new_member_count,
                    )

                if new_member_count != channel.member_count:
                    channel.member_count = new_member_count
                    counters["member_count_refreshed"] += 1

                channel.last_blogger_registry_check_at = now

                if (
                    channel.is_blogger_registry_verified
                    and channel.blogger_registry_verification_method
                    == BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN
                ):
                    try:
                        still_admin = await verify_trustchannelbot_admin(bot, channel.telegram_id)
                    except TrustchannelbotResolutionError:
                        counters["api_failures"] += 1
                        logger.warning(
                            "Trustchannelbot resolution failed for channel %s during "
                            "periodic check — leaving verification untouched",
                            channel.id,
                        )
                        continue

                    if still_admin:
                        counters["still_verified"] += 1
                    else:
                        channel.is_blogger_registry_verified = False
                        channel.blogger_registry_verified_at = None
                        channel.blogger_registry_verification_method = None
                        channel.blogger_registry_verified_by_admin_id = None
                        channel.member_count_at_verification = None
                        counters["verification_lost"] += 1

                        await audit.log(
                            action="blogger_registry_auto_unverified",
                            resource_type="telegram_chat",
                            resource_id=channel.id,
                            user_id=None,
                            extra={
                                "reason": "trustchannelbot_no_longer_admin",
                                "previous_method": (
                                    BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN.value
                                ),
                            },
                        )

                        await notify_owner_verification_lost(
                            session=session,
                            owner_user_id=channel.owner_id,
                            channel_id=channel.id,
                        )

            except Exception:
                counters["api_failures"] += 1
                logger.exception(
                    "Periodic blogger-registry check failed for channel %s",
                    channel.id,
                )

        await session.commit()

    logger.info("BL-107 periodic registry check complete: %s", counters)
    return counters
