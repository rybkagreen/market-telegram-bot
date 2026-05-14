"""SupplementaryAgreementService — генерация дополнительных соглашений (ДС).

Создаёт пару Contract-рядов (`contract_type='supplementary_agreement'`) на каждое
placement: один для рекламодателя, один для владельца канала. `parent_contract_id`
указывает на соответствующий подписанный рамочный договор каждой стороны.

S-48 Pattern 1 (caller-owns): принимает `session` в `__init__`, использует только
`flush()`, никогда не вызывает `commit()` / `rollback()` / `session.begin()`.

Idempotency: повторный вызов `generate_for_placement` для того же placement
возвращает уже существующую пару (`get_by_placement_and_role` per side). При
гонке INSERT защищён частичным UNIQUE-индексом
`uq_contracts_supplementary_placement_role` + откатом по `IntegrityError`.

Sub-stage logging (BL-037): записывает события `supplementary_generated` /
`supplementary_notified` через `ContractRepo.record_event`, схема —
`src/core/schemas/contract_event.py`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings as _settings
from src.constants.fees import (
    OWNER_NET_RATE,
    OWNER_SHARE_RATE,
    PLATFORM_COMMISSION_RATE,
    SERVICE_FEE_RATE,
)
from src.constants.legal import CONTRACT_TEMPLATE_VERSION
from src.core.schemas.contract_event import (
    SupplementaryGeneratedMetadata,
    SupplementaryNotifiedMetadata,
)
from src.core.services.contract_service import (
    _SNAPSHOT_WHITELIST,
    ContractService,
)
from src.db.models.contract import Contract
from src.db.models.placement_request import PlacementRequest, PublicationFormat
from src.db.repositories.contract_repo import ContractRepo
from src.db.repositories.legal_profile_repo import LegalProfileRepo

if TYPE_CHECKING:
    from src.db.models.legal_profile import LegalProfile

logger = logging.getLogger(__name__)


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


_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "contracts"

_SUP_AGREEMENT_OUTPUT_DIR = Path(_settings.contracts_storage_path) / "supplementary_agreements"
_SUP_AGREEMENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


_TEMPLATE_ADVERTISER = "supplementary_agreement_advertiser.html"
_TEMPLATE_OWNER_BY_LEGAL_STATUS: dict[str, str] = {
    "individual": "supplementary_agreement_owner_individual.html",
    "self_employed": "supplementary_agreement_owner_self_employed.html",
    "individual_entrepreneur": "supplementary_agreement_owner_ie.html",
    "legal_entity": "supplementary_agreement_owner_le.html",
}


# Optional ru-locale month names (для шапки даты). Templates also format dates
# via Jinja's strftime fallback; this helper only assembles the city/date line.
_RU_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def _format_ru_date(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return f"{dt.day:02d} {_RU_MONTHS[dt.month - 1]} {dt.year}"


class SupplementaryAgreementService:
    """Сервис генерации ДС (двухсторонней пары)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._contract_repo = ContractRepo(session)
        self._legal_repo = LegalProfileRepo(session)
        self._contract_service = ContractService(session)

    async def generate_for_placement(
        self, placement: PlacementRequest
    ) -> tuple[Contract, Contract]:
        """Сгенерировать пару ДС для placement (рекламодатель + владелец).

        Идемпотентно: если пара уже создана — возвращает существующие строки
        без повторной записи.

        Returns:
            (advertiser_contract, owner_contract).

        Raises:
            ValueError: при отсутствии `final_price`, подписанного рамочного
                договора одной из сторон, или legal_profile одной из сторон.
        """
        if placement.final_price is None:
            raise ValueError(
                f"placement {placement.id} has no final_price — ДС cannot be generated"
            )

        existing_adv = await self._contract_repo.get_by_placement_and_role(
            placement_id=placement.id, role="advertiser"
        )
        existing_own = await self._contract_repo.get_by_placement_and_role(
            placement_id=placement.id, role="owner"
        )
        if existing_adv is not None and existing_own is not None:
            return existing_adv, existing_own

        advertiser_parent = await self._contract_repo.get_framework_contract(
            user_id=placement.advertiser_id, role="advertiser"
        )
        if advertiser_parent is None:
            raise ValueError(
                f"advertiser {placement.advertiser_id} has no signed framework "
                f"contract — ДС for placement {placement.id} cannot be generated"
            )

        owner_parent = await self._contract_repo.get_framework_contract(
            user_id=placement.owner_id, role="owner"
        )
        if owner_parent is None:
            raise ValueError(
                f"owner {placement.owner_id} has no signed framework "
                f"contract — ДС for placement {placement.id} cannot be generated"
            )

        adv_contract = existing_adv or await self._generate_side(
            placement=placement,
            user_id=placement.advertiser_id,
            role="advertiser",
            parent_contract=advertiser_parent,
        )
        own_contract = existing_own or await self._generate_side(
            placement=placement,
            user_id=placement.owner_id,
            role="owner",
            parent_contract=owner_parent,
        )

        return adv_contract, own_contract

    async def _generate_side(
        self,
        placement: PlacementRequest,
        user_id: int,
        role: Literal["owner", "advertiser"],
        parent_contract: Contract,
    ) -> Contract:
        """Создать одну Contract-строку (+PDF) + sub-stage events.

        Race-safe: при срабатывании партициального UNIQUE-индекса
        `uq_contracts_supplementary_placement_role` ловится IntegrityError
        и возвращается строка, созданная конкурирующим вызовом.
        """
        profile = await self._legal_repo.get_by_user_id(user_id)
        if profile is None:
            raise ValueError(
                f"user {user_id} has no legal_profile — ДС for placement "
                f"{placement.id} role={role} cannot be generated"
            )

        snapshot = _build_pii_safe_snapshot(profile)

        contract = Contract(
            user_id=user_id,
            contract_type="supplementary_agreement",
            contract_status="draft",
            placement_id=placement.id,
            parent_contract_id=parent_contract.id,
            role=role,
            legal_status_snapshot=snapshot,
            template_version=CONTRACT_TEMPLATE_VERSION,
        )
        self._session.add(contract)

        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._contract_repo.get_by_placement_and_role(
                placement_id=placement.id, role=role
            )
            if existing is None:
                raise
            return existing

        platform_ctx = await self._contract_service._get_platform_ctx()
        placement_ctx = self._build_placement_ctx(placement, parent_contract)
        ctx = self._build_template_ctx(
            profile=profile,
            placement_ctx=placement_ctx,
            platform_ctx=platform_ctx,
            contract=contract,
        )

        template_path = self._select_template(role=role, legal_status=profile.legal_status)
        html = self._render_template(template_path, ctx)
        pdf_path = self._html_to_pdf(html, contract.id, role)
        if pdf_path is not None:
            contract.pdf_file_path = str(pdf_path)
            await self._session.flush()

        await self._contract_repo.record_event(
            contract_id=contract.id,
            event_type="supplementary_generated",
            actor_user_id=None,
            event_metadata=SupplementaryGeneratedMetadata(
                placement_id=placement.id,
                role=role,
                parent_contract_id=parent_contract.id,
            ).model_dump(),
        )

        try:
            from src.tasks.notification_tasks import notify_supplementary_to_sign

            notify_supplementary_to_sign.apply_async(
                args=[contract.id],
                queue="notifications",
            )
        except Exception as exc:  # noqa: BLE001 — enqueue failures must not abort generation
            logger.warning(
                "Failed to enqueue ДС sign notification for contract %s: %s",
                contract.id,
                exc,
            )
            return contract

        await self._contract_repo.record_event(
            contract_id=contract.id,
            event_type="supplementary_notified",
            actor_user_id=None,
            event_metadata=SupplementaryNotifiedMetadata(
                placement_id=placement.id,
                role=role,
                notification_channel="telegram",
            ).model_dump(),
        )

        return contract

    @staticmethod
    def _select_template(role: Literal["owner", "advertiser"], legal_status: str | None) -> str:
        """Dedicated template router (Q-B.2 — НЕ расширяет `_CONTRACT_TEMPLATE_MAP`)."""
        if role == "advertiser":
            return _TEMPLATE_ADVERTISER
        if role == "owner":
            if legal_status is None or legal_status not in _TEMPLATE_OWNER_BY_LEGAL_STATUS:
                raise ValueError(
                    f"owner legal_status invalid for ДС: {legal_status!r}; "
                    f"valid: {sorted(_TEMPLATE_OWNER_BY_LEGAL_STATUS.keys())}"
                )
            return _TEMPLATE_OWNER_BY_LEGAL_STATUS[legal_status]
        raise ValueError(f"unknown role for ДС: {role!r}")

    @staticmethod
    def _build_placement_ctx(
        placement: PlacementRequest, parent_contract: Contract
    ) -> dict[str, Any]:
        """Placement-specific Jinja2 context vars для ДС templates (Q-B.4).

        Считает суммы по `final_price` и константам ставок, единый источник
        правды — `src/constants/fees.py`. Никаких inline-чисел в шаблонах.
        """
        gross: Decimal = placement.final_price  # type: ignore[assignment]  # validated by caller
        owner_gross = (gross * OWNER_SHARE_RATE).quantize(Decimal("0.01"))
        owner_net = (gross * OWNER_NET_RATE).quantize(Decimal("0.01"))
        platform_commission = (gross * PLATFORM_COMMISSION_RATE).quantize(Decimal("0.01"))
        service_fee = (owner_gross * SERVICE_FEE_RATE).quantize(Decimal("0.01"))

        parent_type_label = (
            "Рамочный договор рекламодателя"
            if parent_contract.role == "advertiser"
            else "Договор с владельцем канала"
        )

        return {
            "parent_contract_number": parent_contract.id,
            "parent_contract_date": _format_ru_date(parent_contract.signed_at),
            "parent_contract_type_label": parent_type_label,
            "placement_id": placement.id,
            "placement_format_human": PublicationFormat.label(placement.publication_format),
            "placement_duration_hours": PublicationFormat.duration_hours(
                placement.publication_format
            ),
            "placement_scheduled_at": (
                placement.final_schedule.strftime("%d.%m.%Y %H:%M")
                if placement.final_schedule is not None
                else "—"
            ),
            "placement_channel_title": placement.channel.title,
            "placement_channel_link": (
                f"@{placement.channel.username}"
                if placement.channel.username
                else f"id={placement.channel.id}"
            ),
            "placement_ad_text": placement.ad_text,
            "placement_gross_amount": _fmt_money(gross),
            "owner_gross_amount": _fmt_money(owner_gross),
            "owner_net_amount": _fmt_money(owner_net),
            "platform_commission_amount": _fmt_money(platform_commission),
            "service_fee_amount": _fmt_money(service_fee),
            # Q-M.4 — erid is generated at escrow time, not at ДС generation.
            "erid_placeholder": "присваивается при регистрации в ОРД перед публикацией",
        }

    @staticmethod
    def _build_template_ctx(
        profile: LegalProfile,
        placement_ctx: dict[str, Any],
        platform_ctx: dict[str, Any],
        contract: Contract,
    ) -> dict[str, Any]:
        """Compose full Jinja2 context: fees + placement + platform + party реквизиты."""
        from src.core.services.contract_service import _build_fee_context

        ctx: dict[str, Any] = {
            "legal_name": getattr(profile, "legal_name", None) or "",
            "inn": getattr(profile, "inn", None) or "",
            "kpp": getattr(profile, "kpp", None) or "",
            "ogrn": getattr(profile, "ogrn", None) or "",
            "ogrnip": getattr(profile, "ogrnip", None) or "",
            "address": getattr(profile, "address", None) or "",
            "tax_regime": getattr(profile, "tax_regime", None) or "",
            "bank_name": getattr(profile, "bank_name", None) or "",
            "bank_bik": getattr(profile, "bank_bik", None) or "",
            "legal_status": getattr(profile, "legal_status", None) or "",
            "contract_date": _format_ru_date(datetime.now(UTC)),
            "contract_id": contract.id,
            "platform_name": "RekHarborBot",
            **_build_fee_context(),
            **placement_ctx,
        }
        ctx.update({k: v for k, v in platform_ctx.items() if v is not None})
        return ctx

    @staticmethod
    def _render_template(template_path: str, ctx: dict[str, Any]) -> str:
        """Render ДС template through shared Jinja2 environment.

        FileSystemLoader rooted at TEMPLATES_DIR.parent so `{% include
        "_partials/..." %}` resolves the same way as in ContractService.
        Fallback to minimal HTML on Jinja exception (mirrors ContractService
        — never raise from template render path).
        """
        if USE_JINJA2 and _TEMPLATES_DIR.exists():
            env = Environment(  # type: ignore[misc]
                loader=FileSystemLoader([str(_TEMPLATES_DIR), str(_TEMPLATES_DIR.parent)]),
                autoescape=select_autoescape(["html", "xml"]),
            )
            try:
                return env.get_template(template_path).render(**ctx)
            except Exception:  # noqa: BLE001
                logger.exception("ДС template render failed: %s", template_path)

        return (
            "<html><body>"
            f"<h1>Дополнительное соглашение №{ctx.get('contract_id')}</h1>"
            f"<p>Шаблон {template_path!r} не загрузился. См. логи.</p>"
            "</body></html>"
        )

    @staticmethod
    def _html_to_pdf(html: str, contract_id: int, role: str) -> Path | None:
        """WeasyPrint render; HTML fallback при недоступности WeasyPrint.

        Возвращает Path к PDF (если PDF сгенерирован) или None (HTML-fallback).
        Mirrors ContractService._html_to_pdf — никогда не raise, чтобы fail в
        PDF-пайплайне не блокировал генерацию ДС-row.
        """
        pdf_path = _SUP_AGREEMENT_OUTPUT_DIR / f"sup_agreement_{contract_id}_{role}.pdf"

        if USE_WEASYPRINT:
            try:
                weasyprint.HTML(string=html).write_pdf(str(pdf_path))  # type: ignore[name-defined]
                return pdf_path
            except Exception as exc:  # noqa: BLE001
                logger.warning("ДС PDF generation failed (contract %s): %s", contract_id, exc)
                return None

        html_path = _SUP_AGREEMENT_OUTPUT_DIR / f"sup_agreement_{contract_id}_{role}.html"
        html_path.write_text(html, encoding="utf-8")
        return None


def _build_pii_safe_snapshot(profile: LegalProfile) -> dict[str, Any]:
    """Whitelist-driven snapshot of LegalProfile fields (mirrors ContractService)."""
    snapshot: dict[str, Any] = {}
    for col in profile.__table__.columns:
        if col.name in _SNAPSHOT_WHITELIST:
            val = getattr(profile, col.name)
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            snapshot[col.name] = val
    return snapshot


def _fmt_money(value: Decimal) -> str:
    """Format Decimal as Russian-style monetary string (1 234,56)."""
    formatted = f"{value:,.2f}"
    # English thousand-sep ',' → Russian ' '; English decimal '.' → Russian ','.
    return formatted.replace(",", " ").replace(".", ",")
