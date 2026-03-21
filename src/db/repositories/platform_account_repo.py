"""PlatformAccountRepository for PlatformAccount model operations."""

from decimal import Decimal

from sqlalchemy import select

from src.db.models.platform_account import PlatformAccount
from src.db.repositories.base import BaseRepository


class PlatformAccountRepository(BaseRepository[PlatformAccount]):
    """Репозиторий для работы с аккаунтом платформы. Singleton с id=1."""

    model = PlatformAccount

    async def get_singleton(self) -> PlatformAccount:
        """Получить singleton аккаунт платформы. Если не существует — создаёт."""
        result = await self.session.get(PlatformAccount, 1)
        if result is None:
            result = PlatformAccount(id=1)
            self.session.add(result)
            await self.session.flush()
        return result

    async def get_for_update(self) -> PlatformAccount:
        """Получить аккаунт платформы с блокировкой строки."""
        result = await self.session.execute(select(PlatformAccount).where(PlatformAccount.id == 1).with_for_update())
        account = result.scalar_one()
        if account is None:
            account = PlatformAccount(id=1)
            self.session.add(account)
            await self.session.flush()
        return account

    async def get_platform_account(self) -> PlatformAccount | None:
        """Получить аккаунт платформы (singleton id=1)."""
        return await self.session.get(PlatformAccount, 1)

    async def add_to_payout_reserved(self, session, amount: Decimal) -> None:
        """Добавить к зарезервированным выплатам."""
        account = await self.get_for_update()
        account.payout_reserved += amount
        await session.flush()

    async def add_to_profit(self, session, amount: Decimal) -> None:
        """Добавить к накопленной прибыли."""
        account = await self.get_for_update()
        account.profit_accumulated += amount
        await session.flush()

    async def complete_payout(self, session, gross_amount: Decimal, net_amount: Decimal) -> None:
        """Завершить выплату — списать с payout_reserved."""
        account = await self.get_for_update()
        account.payout_reserved -= gross_amount
        await session.flush()

PlatformAccountRepo = PlatformAccountRepository
