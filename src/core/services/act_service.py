"""ActService — генерация актов выполненных работ.

Переиспользует Jinja2 + WeasyPrint стек из contract_service.py.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings as _settings
from src.core.services.contract_service import _build_fee_context
from src.core.services.document_number_service import DocumentNumberService
from src.db.models.act import Act
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User
from src.db.repositories.act_repo import ActRepository

logger = logging.getLogger(__name__)

# ─── Jinja2 / WeasyPrint detection (same pattern as contract_service.py) ───

try:
    from jinja2 import (  # type: ignore[import-not-found]
        Environment,
        FileSystemLoader,
        select_autoescape,
    )

    USE_JINJA2 = True
except ImportError:
    USE_JINJA2 = False
    Environment = None  # type: ignore[assignment,misc]

try:
    import weasyprint  # type: ignore[import-not-found]

    USE_WEASYPRINT = True
except ImportError:
    USE_WEASYPRINT = False

# Шаблон акта — рядом с шаблонами договоров
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

# Act templates routing per BL-040 / Промт 15.11.
# Каждый template отражает один из трёх контрактных пар:
#   - platform ↔ advertiser (act_placement.html / act_advertiser.html)
#   - platform ↔ owner (act_owner_*.html, разделены по legal_status owner'а:
#       individual           — НДФЛ 13% (act_owner_fl.html)
#       self_employed        — НПД (act_owner_np.html)
#       individual_entrepreneur — УСН/НДС (act_owner_ie.html)
#       legal_entity         — ОГРН/КПП (act_owner_le.html))
ACT_TEMPLATE_PLATFORM = "acts/act_placement.html"
ACT_TEMPLATE_ADVERTISER = "acts/act_advertiser.html"
ACT_TEMPLATE_MAP_OWNER: dict[str, str] = {
    "individual": "acts/act_owner_fl.html",
    "self_employed": "acts/act_owner_np.html",
    "individual_entrepreneur": "acts/act_owner_ie.html",
    "legal_entity": "acts/act_owner_le.html",
}


def get_act_template(party: str, legal_status: str | None = None) -> str:
    """Resolve act template path по party + legal_status (BL-040 / Промт 15.11).

    Sub-stages (BL-037 sub-stage tracking):
        - 2a. Validate party value (advertiser / owner / platform).
        - 2b. For owner: validate legal_status not None + key exists в map.
        - 2c. Return template path.

    Failure: any invalid combination → raise ValueError. Caller decides
    whether to default или escalate.
    """
    if party == "advertiser":
        return ACT_TEMPLATE_ADVERTISER

    if party == "platform":
        return ACT_TEMPLATE_PLATFORM

    if party == "owner":
        if legal_status is None:
            raise ValueError(
                "owner party requires legal_status, got None. "
                "User.legal_status must be set for act generation."
            )
        if legal_status not in ACT_TEMPLATE_MAP_OWNER:
            raise ValueError(
                f"owner legal_status {legal_status!r} not in ACT_TEMPLATE_MAP_OWNER. "
                f"Valid: {sorted(ACT_TEMPLATE_MAP_OWNER.keys())}."
            )
        return ACT_TEMPLATE_MAP_OWNER[legal_status]

    raise ValueError(
        f"Unknown party {party!r}. Valid: 'advertiser', 'owner', 'platform'."
    )


# Директория для хранения PDF актов
ACTS_OUTPUT_DIR = Path(_settings.contracts_storage_path) / "acts"
ACTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ActService:
    """Сервис для генерации актов выполненных работ.

    Вызывается после удаления опубликованного поста, когда
    placement_request.deleted_at IS NOT NULL.
    """

    @classmethod
    async def generate_for_completed_placement(
        cls, session: AsyncSession, placement: PlacementRequest
    ) -> Act:
        """Сгенерировать акт для завершённого размещения.

        Args:
            session: Асинхронная сессия.
            placement: Заявка на размещение (с загруженными relationships).

        Returns:
            Созданный объект Act.

        Raises:
            ValueError: Если размещение не завершено (deleted_at is None).
        """
        if placement.deleted_at is None:
            raise ValueError(f"Placement {placement.id} not completed yet (deleted_at is None)")

        # Проверяем, нет ли уже акта для этого размещения
        act_repo = ActRepository(session)
        existing = await act_repo.get_by_placement_request(placement.id)
        if existing:
            logger.info(f"Act already exists for placement {placement.id}: {existing.act_number}")
            return existing

        # Загружаем юридические профили
        placement = await cls._load_placement_with_profiles(session, placement.id)

        # Генерируем номер акта
        act_number = await DocumentNumberService.generate_next(session, "АКТ")

        # Подготовка контекста платформы
        platform_ctx = await cls._get_platform_ctx(session)

        # Рендерим шаблон
        html = cls._render_act_template(placement, act_number, platform_ctx)

        # Конвертируем в PDF
        pdf_path = cls._html_to_pdf(html, act_number)
        if pdf_path is None:
            raise RuntimeError(f"PDF generation failed for act {act_number}")

        # Сохраняем акт в БД
        act = Act(
            placement_request_id=placement.id,
            act_number=act_number,
            act_date=placement.deleted_at or datetime.now(UTC),
            pdf_path=str(pdf_path),
            generated_at=datetime.now(UTC),
            meta_json={
                "placement_id": placement.id,
                "advertiser_id": placement.advertiser_id,
                "owner_id": placement.owner_id,
                "final_price": str(placement.final_price or placement.proposed_price),
                "publication_format": placement.publication_format.value
                if hasattr(placement.publication_format, "value")
                else str(placement.publication_format),
                "erid": placement.erid,
            },
        )
        session.add(act)
        await session.flush()
        await session.refresh(act)

        logger.info(f"Act generated: {act_number} for placement {placement.id}, pdf={pdf_path}")

        return act

    @classmethod
    async def _load_placement_with_profiles(
        cls, session: AsyncSession, placement_id: int
    ) -> PlacementRequest:
        """Загрузить placement с advertiser/owner и их legal_profile.

        Returns:
            PlacementRequest с загруженными selectinload relationships.
        """
        result = await session.execute(
            select(PlacementRequest)
            .options(
                selectinload(PlacementRequest.advertiser).selectinload(User.legal_profile),
                selectinload(PlacementRequest.owner).selectinload(User.legal_profile),
                selectinload(PlacementRequest.channel),
            )
            .where(PlacementRequest.id == placement_id)
        )
        placement = result.scalar_one()
        return placement

    @classmethod
    async def _get_platform_ctx(cls, session: AsyncSession) -> dict[str, Any]:
        """Загрузить реквизиты платформы из PlatformAccount (id=1)."""
        from src.db.models.platform_account import PlatformAccount

        account = await session.get(PlatformAccount, 1)
        if not account:
            return {}
        return {
            "platform_legal_name": account.legal_name or "",
            "platform_inn": account.inn or "",
            "platform_kpp": account.kpp or "",
            "platform_ogrn": account.ogrn or "",
            "platform_address": account.address or "",
            "platform_bank_name": account.bank_name or "",
            "platform_bank_account": account.bank_account or "",
            "platform_bank_bik": account.bank_bik or "",
            "platform_bank_corr_account": account.bank_corr_account or "",
        }

    @classmethod
    def _render_act_template(  # NOSONAR: python:S3776
        cls,
        placement: PlacementRequest,
        act_number: str,
        platform_ctx: dict[str, Any] | None = None,
    ) -> str:
        """Отрендерить HTML шаблон акта.

        Контекст шаблона:
            act_number, act_date, advertiser, owner, channel,
            final_price, publication_format, published_at, deleted_at, erid,
            platform_legal_name, platform_inn, ...
        """
        advertiser = placement.advertiser
        owner = placement.owner
        channel = placement.channel

        adv_lp = (
            advertiser.legal_profile
            if hasattr(advertiser, "legal_profile") and advertiser.legal_profile
            else None
        )
        own_lp = (
            owner.legal_profile if hasattr(owner, "legal_profile") and owner.legal_profile else None
        )

        ctx: dict[str, Any] = {
            "act_number": act_number,
            "act_date": (placement.deleted_at or datetime.now(UTC)).strftime("%d.%m.%Y"),
            # Advertiser
            "advertiser_name": advertiser.first_name or advertiser.username or "",
            "advertiser_inn": getattr(adv_lp, "inn", "") or "",
            "advertiser_legal_status": getattr(adv_lp, "legal_status", "") or "",
            # Owner
            "owner_name": owner.first_name or owner.username or "",
            "owner_inn": getattr(own_lp, "inn", "") or "",
            "owner_legal_status": getattr(own_lp, "legal_status", "") or "",
            # Channel
            "channel_name": getattr(channel, "title", "") or getattr(channel, "username", "") or "",
            "channel_id": channel.id if channel else None,
            # Placement details
            "final_price": placement.final_price or placement.proposed_price,
            "publication_format": placement.publication_format.value
            if hasattr(placement.publication_format, "value")
            else str(placement.publication_format),
            "published_at": (
                placement.published_at.strftime("%d.%m.%Y") if placement.published_at else ""
            ),
            "deleted_at": (
                placement.deleted_at.strftime("%d.%m.%Y") if placement.deleted_at else ""
            ),
            "erid": placement.erid or "",
            "ad_text": placement.ad_text[:200] if placement.ad_text else "",
            **_build_fee_context(),
        }
        if platform_ctx:
            ctx.update({k: v for k, v in platform_ctx.items() if v is not None})

        if USE_JINJA2 and TEMPLATES_DIR.exists():
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
            )
            try:
                return env.get_template(get_act_template("platform")).render(**ctx)
            except Exception:
                logger.exception(f"Jinja2 template render failed for act {act_number}")

        # Fallback: plain HTML
        return (
            f"<html><body>"
            f"<h1>Акт №{act_number}</h1>"
            f"<p>Дата: {ctx['act_date']}</p>"
            f"<p>Исполнитель: {ctx.get('platform_legal_name', 'RekHarborBot')}</p>"
            f"<p>Заказчик: {ctx['advertiser_name']}</p>"
            f"<p>Услуга: размещение рекламы, формат {ctx['publication_format']}</p>"
            f"<p>Сумма: {ctx['final_price']} ₽</p>"
            f"</body></html>"
        )

    @classmethod
    def _html_to_pdf(cls, html_content: str, act_number: str) -> Path | None:
        """Конвертировать HTML в PDF (если WeasyPrint доступен).

        Args:
            html_content: HTML содержимое акта.
            act_number: Номер акта для имени файла.

        Returns:
            Путь к PDF файлу или None при ошибке.
        """
        output_path = ACTS_OUTPUT_DIR / f"{act_number}.pdf"

        if USE_WEASYPRINT:
            try:
                weasyprint.HTML(string=html_content).write_pdf(str(output_path))  # type: ignore[name-defined]
                return output_path
            except Exception as e:
                logger.warning(f"Act PDF generation failed: {e}")
                return None
        else:
            # Save HTML as fallback
            html_path = ACTS_OUTPUT_DIR / f"{act_number}.html"
            html_path.write_text(html_content, encoding="utf-8")
            return None
