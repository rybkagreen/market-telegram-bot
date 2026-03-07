"""
B2B Package Service — сервис для управления пакетными предложениями.
Спринт 3 — B2B-маркетплейс для агентств и крупных рекламодателей.
"""

import logging
from typing import Any

from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


class B2BPackageService:
    """
    Сервис для управления B2B-пакетами.

    Методы:
        get_packages_by_niche: Получить пакеты по нише
        validate_package_channels: Проверить каналы в пакете
        get_package_actual_reach: Получить фактический охват пакета
        calculate_package_discount: Рассчитать скидку пакета
    """

    # Описание ниш для пользователей
    NICHE_DESCRIPTIONS = {
        "it": "💻 IT и технологии — разработчики, стартапы, digital-специалисты",
        "business": "💼 Бизнес — предприниматели, менеджеры, корпоративные клиенты",
        "realestate": "🏠 Недвижимость — застройщики, риелторы, инвесторы",
        "crypto": "🔗 Криптовалюты — трейдеры, инвесторы, блокчейн-энтузиасты",
        "marketing": "📈 Маркетинг — маркетологи, SMM-специалисты, агентства",
        "finance": "💰 Финансы — инвесторы, трейдеры, финансовые консультанты",
    }

    def __init__(self) -> None:
        """Инициализация сервиса."""
        pass

    async def get_packages_by_niche(
        self,
        niche: str,
    ) -> list[dict[str, Any]]:
        """
        Получить пакеты по нише.

        Args:
            niche: Название ниши (it, business, realestate, crypto, marketing, finance).

        Returns:
            Список активных пакетов.
        """
        from sqlalchemy import select

        from src.db.models.b2b_package import B2BPackage

        async with async_session_factory() as session:
            stmt = (
                select(B2BPackage)
                .where(
                    B2BPackage.niche == niche,
                    B2BPackage.is_active == True,  # noqa: E712
                )
                .order_by(B2BPackage.price.asc())
            )
            result = await session.execute(stmt)
            packages = list(result.scalars().all())

            return [
                {
                    "id": pkg.id,
                    "name": pkg.name,
                    "niche": pkg.niche,
                    "description": pkg.description,
                    "channels_count": pkg.channels_count,
                    "guaranteed_reach": pkg.guaranteed_reach,
                    "min_er": pkg.min_er,
                    "price": float(pkg.price),
                    "discount_pct": pkg.discount_pct,
                    "is_available": pkg.is_available,
                }
                for pkg in packages
            ]

    async def get_all_packages(self) -> dict[str, list[dict[str, Any]]]:
        """
        Получить все пакеты по нишам.

        Returns:
            dict с нишами как ключами и списками пакетов.
        """
        result = {}
        for niche in self.NICHE_DESCRIPTIONS:
            result[niche] = await self.get_packages_by_niche(niche)
        return result

    async def validate_package_channels(
        self,
        package_id: int,
    ) -> dict[str, Any]:
        """
        Проверить каналы в пакете на активность.

        Args:
            package_id: ID пакета.

        Returns:
            dict с valid, active_channels, inactive_channels.
        """

        from src.db.models.analytics import TelegramChat
        from src.db.models.b2b_package import B2BPackage

        async with async_session_factory() as session:
            package = await session.get(B2BPackage, package_id)
            if not package:
                return {"error": "Package not found"}

            channel_ids = package.channel_ids
            active_channels = []
            inactive_channels = []

            for channel_id in channel_ids:
                channel = await session.get(TelegramChat, channel_id)
                if channel and channel.is_active and channel.is_accepting_ads:
                    active_channels.append(channel_id)
                else:
                    inactive_channels.append(channel_id)

            return {
                "package_id": package_id,
                "valid": len(inactive_channels) == 0,
                "active_channels": active_channels,
                "inactive_channels": inactive_channels,
                "total_channels": len(channel_ids),
            }

    async def get_package_actual_reach(
        self,
        package_id: int,
    ) -> dict[str, Any]:
        """
        Получить фактический охват пакета на текущий момент.

        Args:
            package_id: ID пакета.

        Returns:
            dict с actual_reach, guaranteed_reach, difference.
        """
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat
        from src.db.models.b2b_package import B2BPackage

        async with async_session_factory() as session:
            package = await session.get(B2BPackage, package_id)
            if not package:
                return {"error": "Package not found"}

            # Получаем каналы пакета
            stmt = (
                select(TelegramChat)
                .where(
                    TelegramChat.id.in_(package.channel_ids),
                    TelegramChat.is_active == True,  # noqa: E712
                )
            )
            result = await session.execute(stmt)
            channels = list(result.scalars().all())

            # Считаем фактический охват
            actual_reach = sum(ch.last_avg_views or 0 for ch in channels)

            return {
                "package_id": package_id,
                "actual_reach": actual_reach,
                "guaranteed_reach": package.guaranteed_reach,
                "difference": actual_reach - package.guaranteed_reach,
                "meets_guarantee": actual_reach >= package.guaranteed_reach,
            }

    def calculate_package_discount(
        self,
        package_id: int,
    ) -> dict[str, Any]:
        """
        Рассчитать скидку пакета по сравнению с разовыми размещениями.

        Args:
            package_id: ID пакета.

        Returns:
            dict с regular_price, package_price, discount_amount, discount_pct.
        """
        # Заглушка — в реальности нужно считать сумму разовых размещений
        # по всем каналам пакета
        return {
            "package_id": package_id,
            "regular_price": 0,  # Placeholder
            "package_price": 0,  # Placeholder
            "discount_amount": 0,
            "discount_pct": 0,
        }

    async def generate_mediakit_pdf(
        self,
        channel_id: int,
    ) -> bytes:
        """
        Сгенерировать PDF-медиакит канала.

        Args:
            channel_id: ID канала в БД.

        Returns:
            PDF файл в bytes.
        """
        from io import BytesIO

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        from src.db.models.analytics import TelegramChat

        async with async_session_factory() as session:
            channel = await session.get(TelegramChat, channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")

            # Создаём PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()

            # Заголовок
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=18,
                spaceAfter=20,
            )

            elements = []
            elements.append(
                Paragraph(f"Медиакит: @{channel.username or channel.title}", title_style)
            )
            elements.append(Spacer(1, 0.2 * inch))  # type: ignore[arg-type]

            # Основная информация
            info_data = [
                ["Параметр", "Значение"],
                ["Название", channel.title or "Без названия"],
                ["Username", f"@{channel.username}" if channel.username else "Не указан"],
                ["Подписчики", f"{channel.member_count:,}"],
                ["Средние просмотры", f"{channel.last_avg_views:,}"],
                ["ER", f"{channel.last_er:.2f}%"],
                ["Тематика", channel.topic or "Не указана"],
                ["Цена за пост", f"{channel.price_per_post or 0} ₽"],
            ]

            info_table = Table(info_data, colWidths=[2.5 * inch, 2.5 * inch])
            info_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ]
                )
            )

            elements.append(info_table)  # type: ignore[arg-type]
            elements.append(Spacer(1, 0.5 * inch))  # type: ignore[arg-type]

            # Описание
            if channel.description:
                desc_style = ParagraphStyle(
                    "Description",
                    parent=styles["Normal"],
                    fontSize=11,
                )
                elements.append(Paragraph("<b>Описание:</b>", desc_style))
                elements.append(Spacer(1, 0.1 * inch))  # type: ignore[arg-type]
                elements.append(Paragraph(channel.description, desc_style))
                elements.append(Spacer(1, 0.3 * inch))  # type: ignore[arg-type]

            # Контакты
            contact_style = ParagraphStyle(
                "Contact",
                parent=styles["Normal"],
                fontSize=11,
                textColor=colors.blue,
            )
            elements.append(
                Paragraph("📩 Для размещения: обратитесь к администратору канала", contact_style)
            )

            # Build PDF
            doc.build(elements)  # type: ignore[arg-type]

            pdf_data = buffer.getvalue()
            buffer.close()

            return pdf_data


# Глобальный экземпляр
b2b_package_service = B2BPackageService()
