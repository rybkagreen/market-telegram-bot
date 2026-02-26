"""
Notification Repository для работы с уведомлениями пользователей.
"""

from datetime import UTC
from typing import Any

from sqlalchemy import Integer, Select, and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.notification import Notification, NotificationType
from src.db.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """
    Репозиторий для работы с уведомлениями.

    Методы:
        create_notification: Создать уведомление
        get_unread_count: Получить количество непрочитанных уведомлений
        get_user_notifications: Получить уведомления пользователя
        mark_as_read: Отметить уведомление как прочитанное
        mark_all_as_read: Отметить все уведомления пользователя как прочитанные
        delete_old: Удалить старые уведомления
    """

    model = Notification

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализация репозитория.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        super().__init__(session)

    async def create_notification(
        self,
        user_id: int,
        message: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        title: str | None = None,
        campaign_id: int | None = None,
        transaction_id: int | None = None,
        error_code: str | None = None,
    ) -> Notification:
        """
        Создать уведомление.

        Args:
            user_id: ID пользователя.
            message: Текст сообщения.
            notification_type: Тип уведомления.
            title: Заголовок (опционально).
            campaign_id: ID кампании (опционально).
            transaction_id: ID транзакции (опционально).
            error_code: Код ошибки (опционально).

        Returns:
            Созданное уведомление.
        """
        return await super().create(
            {
                "user_id": user_id,
                "notification_type": notification_type,
                "message": message,
                "title": title,
                "campaign_id": campaign_id,
                "transaction_id": transaction_id,
                "error_code": error_code,
            }
        )

    async def get_unread_count(self, user_id: int) -> int:
        """
        Получить количество непрочитанных уведомлений пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Количество непрочитанных уведомлений.
        """
        query = (
            select(func.count())
            .select_from(Notification)
            .where(and_(Notification.user_id == user_id, Notification.is_read.is_(False)))
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
        notification_type: NotificationType | None = None,
    ) -> list[Notification]:
        """
        Получить уведомления пользователя с пагинацией.

        Args:
            user_id: ID пользователя.
            limit: Максимальное количество записей.
            offset: Смещение.
            unread_only: Только непрочитанные.
            notification_type: Фильтр по типу уведомления.

        Returns:
            Список уведомлений.
        """
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        if notification_type is not None:
            query = query.where(Notification.notification_type == notification_type)

        query = query.order_by(desc(Notification.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: int) -> bool:
        """
        Отметить уведомление как прочитанное.

        Args:
            notification_id: ID уведомления.

        Returns:
            True если обновлено.
        """
        notification = await self.get_by_id(notification_id)
        if notification is None:
            return False

        notification.is_read = True
        await self.session.flush()
        await self.session.refresh(notification)
        return True

    async def mark_all_as_read(self, user_id: int) -> int:
        """
        Отметить все уведомления пользователя как прочитанные.

        Args:
            user_id: ID пользователя.

        Returns:
            Количество обновлённых записей.
        """
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
            .values(is_read=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount  # type: ignore[attr-defined]

    async def delete_old(
        self,
        user_id: int | None = None,
        days_old: int = 30,
    ) -> int:
        """
        Удалить старые уведомления.

        Args:
            user_id: ID пользователя (опционально, если None — для всех).
            days_old: Возраст в днях.

        Returns:
            Количество удалённых записей.
        """
        from datetime import datetime, timedelta

        from sqlalchemy import delete

        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        stmt = delete(Notification).where(Notification.created_at < cutoff_date)

        if user_id is not None:
            stmt = stmt.where(Notification.user_id == user_id)

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount  # type: ignore[attr-defined]

    async def get_statistics(self, user_id: int | None = None) -> dict[str, Any]:
        """
        Получить статистику уведомлений.

        Args:
            user_id: ID пользователя (опционально, если None — для всех).

        Returns:
            Словарь со статистикой.
        """
        query = select(
            Notification.notification_type,
            func.count().label("total"),
            func.sum(func.cast(Notification.is_read, Integer)).label("read"),
        ).group_by(Notification.notification_type)

        if user_id is not None:
            query = query.where(Notification.user_id == user_id)

        result = await self.session.execute(query)
        rows = result.all()

        return {
            "total": sum(row.total for row in rows),
            "read": sum(row.read or 0 for row in rows),
            "unread": sum(row.total - (row.read or 0) for row in rows),
            "by_type": {
                row.notification_type.value: {
                    "total": row.total,
                    "read": row.read or 0,
                    "unread": row.total - (row.read or 0),
                }
                for row in rows
            },
        }

    def get_query(self) -> Select[tuple[Notification]]:
        """
        Получить базовый query для построения сложных запросов.

        Returns:
            SQLAlchemy Select query.
        """
        return select(Notification)
