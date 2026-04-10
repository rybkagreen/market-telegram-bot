"""PlatformQuarterlyRevenueRepository for PlatformQuarterlyRevenue model operations."""

from sqlalchemy import func, select

from src.db.models.platform_quarterly_revenue import PlatformQuarterlyRevenue
from src.db.repositories.base import BaseRepository


class PlatformQuarterlyRevenueRepository(BaseRepository[PlatformQuarterlyRevenue]):
    """Репозиторий для работы с квартальной выручкой платформы."""

    model = PlatformQuarterlyRevenue

    async def get_by_year(self, year: int) -> list[PlatformQuarterlyRevenue]:
        """Получить записи выручки за год."""
        result = await self.session.execute(
            select(PlatformQuarterlyRevenue)
            .where(PlatformQuarterlyRevenue.year == year)
            .order_by(PlatformQuarterlyRevenue.quarter)
        )
        return list(result.scalars().all())

    async def get_by_year_quarter(self, year: int, quarter: int) -> PlatformQuarterlyRevenue | None:
        """Получить запись выручки за конкретный квартал."""
        result = await self.session.execute(
            select(PlatformQuarterlyRevenue).where(
                PlatformQuarterlyRevenue.year == year,
                PlatformQuarterlyRevenue.quarter == quarter,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest(self) -> PlatformQuarterlyRevenue | None:
        """Получить последнюю запись выручки."""
        result = await self.session.execute(
            select(PlatformQuarterlyRevenue)
            .order_by(
                PlatformQuarterlyRevenue.year.desc(),
                PlatformQuarterlyRevenue.quarter.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_total_revenue(self, year: int) -> float:
        """Получить общую выручку за год."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(PlatformQuarterlyRevenue.revenue), 0)).where(
                PlatformQuarterlyRevenue.year == year
            )
        )
        return float(result.scalar_one() or 0)

    async def upsert(
        self, year: int, quarter: int, revenue: float, placements: int = 0, payouts: float = 0
    ) -> PlatformQuarterlyRevenue:
        """Создать или обновить запись квартальной выручки."""
        existing = await self.get_by_year_quarter(year, quarter)
        if existing:
            existing.revenue = revenue
            existing.placements = placements
            existing.payouts = payouts
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        record = PlatformQuarterlyRevenue(
            year=year,
            quarter=quarter,
            revenue=revenue,
            placements=placements,
            payouts=payouts,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record
