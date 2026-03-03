"""
User Repository для работы с пользователями.
Расширяет BaseRepository специфичными методами для User.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User, UserPlan
from src.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Репозиторий для работы с пользователями.

    Методы:
        get_by_telegram_id: Получить пользователя по Telegram ID.
        create_or_update: Создать или обновить пользователя.
        update_balance: Атомарно обновить баланс.
        get_with_stats: Получить пользователя со статистикой кампаний.
        get_by_referral_code: Получить пользователя по реферальному коду.
        generate_unique_referral_code: Сгенерировать уникальный реферальный код.
    """

    model = User

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """
        Получить пользователя по Telegram ID.

        Args:
            telegram_id: Telegram ID пользователя.

        Returns:
            Пользователь или None.
        """
        return await self.find_one(User.telegram_id == telegram_id)

    async def get_by_username(self, username: str) -> User | None:
        """
        Получить пользователя по username.

        Args:
            username: Username пользователя.

        Returns:
            Пользователь или None.
        """
        return await self.find_one(User.username == username)

    async def create_or_update(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
        **kwargs: Any,
    ) -> User:
        """
        Создать нового пользователя или обновить существующего.

        Args:
            telegram_id: Telegram ID пользователя.
            username: Username пользователя.
            first_name: Имя пользователя.
            last_name: Фамилия пользователя.
            language_code: Язык пользователя.
            **kwargs: Дополнительные атрибуты.

        Returns:
            Пользователь (созданный или обновленный).
        """
        user = await self.get_by_telegram_id(telegram_id)

        if user is None:
            # Генерируем реферальный код
            referral_code = await self.generate_unique_referral_code(telegram_id)
            user = await self.create(
                {
                    "telegram_id": telegram_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "language_code": language_code or "ru",
                    "referral_code": referral_code,
                    **kwargs,
                }
            )
        else:
            # Обновляем данные
            update_data = {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "language_code": language_code,
                **kwargs,
            }
            # Фильтруем None значения
            update_data = {k: v for k, v in update_data.items() if v is not None}
            if update_data:
                await self.update(user.id, update_data)
                await self.refresh(user)

        return user

    async def update_balance(
        self,
        user_id: int,
        delta: Decimal,
        *,
        dry_run: bool = False,
    ) -> tuple[Decimal, Decimal]:
        """
        Атомарно обновить баланс пользователя.

        Использует SQL UPDATE с RETURNING для атомарности.

        Args:
            user_id: ID пользователя в БД.
            delta: Сумма изменения (положительная для пополнения,
                   отрицательная для списания).
            dry_run: Если True, не применять изменения.

        Returns:
            Кортеж (баланс до, баланс после).

        Raises:
            ValueError: Если пользователь не найден.
            ValueError: Если баланс становится отрицательным.
        """
        # Получаем текущего пользователя
        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User with id {user_id} not found")

        balance_before = user.balance
        balance_after = balance_before + delta

        if balance_after < Decimal("0.00"):
            raise ValueError(f"Insufficient balance: {balance_before} + {delta} = {balance_after}")

        if not dry_run:
            # Атомарное обновление через SQL
            from sqlalchemy import update

            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(balance=balance_after)
                .returning(User.balance)
            )
            await self.session.execute(stmt)
            await self.session.flush()

            # Обновляем локальный объект
            user.balance = balance_after

        return balance_before, balance_after

    async def get_with_stats(self, user_id: int) -> dict[str, Any]:
        """
        Получить пользователя со статистикой кампаний.

        Args:
            user_id: ID пользователя в БД.

        Returns:
            Словарь с пользователем и статистикой.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User with id {user_id} not found")

        # Статистика кампаний
        from src.db.models.campaign import Campaign, CampaignStatus

        stats_query = select(
            func.count(Campaign.id).label("total_campaigns"),
            func.sum(
                case(
                    (Campaign.status == CampaignStatus.RUNNING, 1),
                    else_=0,
                )
            ).label("active_campaigns"),
            func.sum(
                case(
                    (Campaign.status == CampaignStatus.DONE, 1),
                    else_=0,
                )
            ).label("completed_campaigns"),
            func.coalesce(func.sum(Campaign.cost), 0).label("total_spent"),
        ).where(Campaign.user_id == user_id)

        result = await self.session.execute(stats_query)
        stats = result.one()

        return {
            "user": user,
            "total_campaigns": stats.total_campaigns or 0,
            "active_campaigns": stats.active_campaigns or 0,
            "completed_campaigns": stats.completed_campaigns or 0,
            "total_spent": Decimal(str(stats.total_spent or 0)),
        }

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        """
        Получить пользователя по реферальному коду.

        Args:
            referral_code: Реферальный код.

        Returns:
            Пользователь или None.
        """
        return await self.find_one(User.referral_code == referral_code)

    async def get_referrers_count(self, user_id: int) -> int:
        """
        Получить количество рефералов пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            Количество рефералов.
        """
        return await self.count(User.referred_by_id == user_id)

    async def get_referrers(self, user_id: int, limit: int = 100) -> list[User]:
        """
        Получить список рефералов пользователя.

        Args:
            user_id: ID пользователя.
            limit: Максимальное количество результатов.

        Returns:
            Список рефералов.
        """
        return await self.find_many(User.referred_by_id == user_id, limit=limit)

    async def generate_unique_referral_code(
        self,
        telegram_id: int,
        length: int = 8,
    ) -> str:
        """
        Сгенерировать уникальный реферальный код.

        Args:
            telegram_id: Telegram ID для генерации кода.
            length: Длина кода.

        Returns:
            Уникальный реферальный код.
        """
        import hashlib
        import time

        # Генерируем код на основе telegram_id и timestamp
        hash_input = f"{telegram_id}_{time.time()}"
        hash_bytes = hashlib.md5(hash_input.encode()).hexdigest()
        referral_code = hash_bytes[:length].upper()

        # Проверяем уникальность
        existing = await self.get_by_referral_code(referral_code)
        if existing is not None:
            # Рекурсивно генерируем новый код
            return await self.generate_unique_referral_code(telegram_id, length + 1)

        return referral_code

    async def get_active_users_count(self) -> int:
        """
        Получить количество активных пользователей.

        Returns:
            Количество активных пользователей.
        """
        return await self.count(User.is_active == True)  # noqa: E712

    async def get_users_for_notification(
        self,
        min_balance: Decimal = Decimal("0.00"),
        max_balance: Decimal = Decimal("50.00"),
    ) -> list[User]:
        """
        Получить пользователей для уведомления о низком балансе.

        Args:
            min_balance: Минимальный баланс.
            max_balance: Максимальный баланс.

        Returns:
            Список пользователей.
        """
        return await self.find_many(
            User.is_active == True,  # noqa: E712
            User.is_banned == False,  # noqa: E712
            User.balance >= min_balance,
            User.balance <= max_balance,
        )

    def get_query_with_campaigns(self) -> Select[tuple[User]]:
        """
        Получить query с подгрузкой кампаний.

        Returns:
            SQLAlchemy Select query.
        """
        from sqlalchemy.orm import selectinload

        return select(self.model).options(selectinload(User.campaigns))

    async def get_users_with_low_balance(
        self,
        threshold: Decimal,
    ) -> list[User]:
        """
        Получить пользователей с низким балансом.

        Args:
            threshold: Порог баланса.

        Returns:
            Список пользователей.
        """
        return await self.find_many(
            User.is_active == True,  # noqa: E712
            User.is_banned == False,  # noqa: E712
            User.balance < threshold,
        )

    async def update_credits(self, user_id: int, delta: int) -> int:
        """
        Атомарно изменить кредиты пользователя.

        Args:
            user_id: ID пользователя в БД.
            delta: Изменение (положительное — пополнение, отрицательное — списание).

        Returns:
            Новый баланс кредитов.

        Raises:
            ValueError: если credits уйдут в минус.
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(User)
            .where(User.id == user_id, User.credits + delta >= 0)
            .values(credits=User.credits + delta)
            .returning(User.credits)
        )
        row = result.fetchone()
        if row is None:
            raise ValueError(f"Недостаточно кредитов (user_id={user_id}, delta={delta})")
        await self.session.flush()  # Только flush, коммит на уровне хендлера
        return row[0]

    async def increment_ai_usage(self, user_id: int) -> None:
        """
        Увеличить счётчик использования ИИ на 1.

        Args:
            user_id: ID пользователя в БД.
        """
        from sqlalchemy import update

        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(ai_generations_used=User.ai_generations_used + 1)
        )
        await self.session.commit()

    async def reset_ai_usage(self, user_id: int) -> None:
        """
        Сбросить счётчик ИИ (при продлении тарифа).

        Args:
            user_id: ID пользователя в БД.
        """
        from sqlalchemy import update

        await self.session.execute(
            update(User).where(User.id == user_id).values(ai_generations_used=0)
        )
        await self.session.commit()

    async def expire_plan(self, user_id: int) -> None:
        """
        Сбросить тариф на FREE при истечении.

        Args:
            user_id: ID пользователя в БД.
        """
        from sqlalchemy import update

        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                plan=UserPlan.FREE,
                plan_expires_at=None,
                ai_generations_used=0,
            )
        )
        await self.session.commit()

    async def toggle_notifications(self, user_id: int) -> bool:
        """
        Переключить уведомления пользователя.
        Возвращает новое значение (True = включены).

        Args:
            user_id: ID пользователя в БД.

        Returns:
            Новое значение notifications_enabled.
        """
        user = await self.get_by_id(user_id)
        if user:
            user.notifications_enabled = not user.notifications_enabled
            await self.session.commit()
            return user.notifications_enabled
        return False

    async def toggle_notifications_by_db_id(self, db_id: int) -> bool:
        """
        Переключить уведомления пользователя по DB ID (для админки).
        Возвращает новое значение (True = включены).

        Args:
            db_id: ID пользователя в БД.

        Returns:
            Новое значение notifications_enabled.
        """
        user = await self.get_by_id(db_id)
        if user:
            user.notifications_enabled = not user.notifications_enabled
            await self.session.commit()
            return user.notifications_enabled
        return False
