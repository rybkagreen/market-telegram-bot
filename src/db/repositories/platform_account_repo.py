"""
PlatformAccountRepository for PlatformAccount model operations.
"""

from sqlalchemy import select

from src.db.models.platform_account import PlatformAccount
from src.db.repositories.base import BaseRepository


class PlatformAccountRepository(BaseRepository[PlatformAccount]):
    """
    Репозиторий для работы с аккаунтом платформы.
    Singleton с id=1.
    """

    model = PlatformAccount

    async def get_singleton(self) -> PlatformAccount:
        """
        Получить singleton аккаунт платформы.

        Если не существует — создаёт.
        """
        result = await self.session.get(PlatformAccount, 1)
        if result is None:
            result = PlatformAccount(id=1)
            self.session.add(result)
            await self.session.flush()
        return result

    async def get_for_update(self) -> PlatformAccount:
        """
        Получить аккаунт платформы с блокировкой строки.

        Для атомарных операций обновления.
        """
        result = await self.session.execute(
            select(PlatformAccount)
            .where(PlatformAccount.id == 1)
            .with_for_update()
        )
        account = result.scalar_one()
        if account is None:
            account = PlatformAccount(id=1)
            self.session.add(account)
            await self.session.flush()
        return account
