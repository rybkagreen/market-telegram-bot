"""
ContractService — генерация и подписание договоров.
S2: создание договоров, подпись, принятие правил платформы.
PDF генерация через WeasyPrint (опционально), fallback — HTML.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings as _settings
from src.constants.legal import CONTRACT_TEMPLATE_VERSION
from src.db.models.contract import Contract
from src.db.models.user import User
from src.db.repositories.contract_repo import ContractRepo
from src.db.repositories.legal_profile_repo import LegalProfileRepo

logger = logging.getLogger(__name__)

KEP_REQUIRED_STATUSES: frozenset[str] = frozenset(
    {"legal_entity", "individual_entrepreneur"}
)  # These legal statuses benefit from KEP for tax accounting purposes

# Detect optional dependencies
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

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "contracts"

# Explicit whitelist for legal_status_snapshot stored in contracts.
# NEVER include passport data, bank account numbers, or document file IDs.
_SNAPSHOT_WHITELIST = frozenset(
    {
        "legal_status",
        "inn",
        "kpp",
        "ogrn",
        "ogrnip",
        "legal_name",
        "address",
        "tax_regime",
        "bank_name",
        "bank_bik",
        "is_verified",
        "created_at",
        "updated_at",
    }
)
PLATFORM_RULES_FILE = "platform_rules.html"

CONTRACTS_OUTPUT_DIR = Path(_settings.contracts_storage_path)
CONTRACTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_CONTRACT_TEMPLATE_MAP: dict[str, dict[str, str]] = {
    "owner_service": {
        "legal_entity": "owner_service_legal_entity.html",
        "individual_entrepreneur": "owner_service_ie.html",
        "self_employed": "owner_service_self_employed.html",
        "individual": "owner_service_individual.html",
    },
    "advertiser_campaign": {"_default": "advertiser_campaign.html"},
    "advertiser_framework": {"_default": "advertiser_campaign.html"},
    "platform_rules": {"_default": PLATFORM_RULES_FILE},
    "privacy_policy": {"_default": PLATFORM_RULES_FILE},
}


class ContractService:
    """Сервис для генерации и подписания договоров."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_platform_ctx(self) -> dict:
        """Загрузить реквизиты платформы из БД для подстановки в шаблоны."""
        from src.db.models.platform_account import PlatformAccount

        account = await self.session.get(PlatformAccount, 1)
        if not account:
            return {}
        return {
            "platform_legal_name": account.legal_name,
            "platform_inn": account.inn,
            "platform_kpp": account.kpp,
            "platform_ogrn": account.ogrn,
            "platform_address": account.address,
            "platform_bank_name": account.bank_name,
            "platform_bank_account": account.bank_account,
            "platform_bank_bik": account.bank_bik,
            "platform_bank_corr_account": account.bank_corr_account,
        }

    async def generate_contract(
        self,
        user_id: int,
        contract_type: str,
        placement_request_id: int | None = None,
    ) -> Contract:
        """Сгенерировать договор и сохранить в БД."""
        # --- Deduplication check (S7 addition) ---
        # For type-level contracts (owner_service, platform_rules, privacy_policy),
        # return existing non-expired contract instead of creating duplicates.
        if contract_type != "advertiser_campaign":
            existing = await ContractRepo(self.session).get_by_user_and_type(user_id, contract_type)
            if existing and existing.contract_status not in ("cancelled", "expired"):
                return existing
        # --- end deduplication check ---

        legal_repo = LegalProfileRepo(self.session)
        profile = await legal_repo.get_by_user_id(user_id)

        # Build snapshot using explicit whitelist — never include PII or bank accounts
        snapshot: dict = {}
        if profile:
            for col in profile.__table__.columns:
                if col.name in _SNAPSHOT_WHITELIST:
                    val = getattr(profile, col.name)
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    snapshot[col.name] = val

        result = await self.session.execute(
            insert(Contract)
            .values(
                user_id=user_id,
                contract_type=contract_type,
                contract_status="pending",
                placement_request_id=placement_request_id,
                legal_status_snapshot=snapshot,
                template_version=CONTRACT_TEMPLATE_VERSION,
            )
            .returning(Contract)
        )
        contract = result.scalar_one()
        # NOTE: flush() intentionally moved AFTER _render_template — flush() expiries ORM
        # objects in the session (including profile). contract.id is already available from
        # RETURNING, so flushing here is not needed.

        # Render template + generate PDF (profile must be accessed before flush)
        platform_ctx = await self._get_platform_ctx()
        html = self._render_template(contract_type, profile, contract.id, platform_ctx)
        await self.session.flush()
        pdf_path = self._html_to_pdf(html, contract.id)
        if pdf_path:
            await self.session.execute(
                sa_update(Contract)
                .where(Contract.id == contract.id)
                .values(pdf_file_path=str(pdf_path))
            )
            await self.session.flush()
            contract.pdf_file_path = str(pdf_path)

        return contract

    async def sign_contract(
        self,
        contract_id: int,
        user_id: int,
        method: str,
        sms_code: str | None = None,
        ip_address: str | None = None,
    ) -> Contract:
        """Подписать договор."""
        result = await self.session.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        if contract.user_id != user_id:
            raise PermissionError("Contract does not belong to user")
        if contract.contract_status not in ("pending", "draft"):
            raise ValueError(f"Contract status is {contract.contract_status}, cannot sign")

        # SMS stub: any 4-digit code is valid for MVP
        if method == "sms_code" and sms_code and not sms_code.isdigit():
            raise ValueError("Invalid SMS code format")

        repo = ContractRepo(self.session)
        signed = await repo.mark_signed(contract_id, method, ip_address)

        # --- Record signature evidence (S8) ---
        import hashlib

        pdf_path = contract.pdf_file_path
        if pdf_path:
            try:
                doc_hash = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
            except Exception:
                doc_hash = hashlib.sha256(f"contract_{contract_id}_v1.0".encode()).hexdigest()
        else:
            doc_hash = hashlib.sha256(f"contract_{contract_id}_v1.0".encode()).hexdigest()

        user_result = await self.session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.legal_profile))
        )
        signing_user = user_result.scalar_one_or_none()
        _lp = signing_user.legal_profile if signing_user is not None else None
        legal_status = _lp.legal_status if _lp is not None else "unknown"
        telegram_id = signing_user.telegram_id if signing_user is not None else user_id

        await ContractRepo(self.session).create_signature(
            contract_id=contract_id,
            user_id=user_id,
            telegram_id=telegram_id,
            role=contract.role or "unknown",
            legal_status=str(legal_status),
            signature_method=method,
            document_hash=doc_hash,
            template_version=contract.template_version,
            ip_address=ip_address,
        )
        # --- end signature evidence ---

        return signed

    async def accept_platform_rules(self, user_id: int) -> None:
        """Принять правила платформы (единый документ: правила + конфиденциальность).

        Создаёт/обновляет один контракт типа platform_rules.
        Для обратной совместимости: если уже есть privacy_policy — обновляет и его.
        """
        repo = ContractRepo(self.session)
        now = datetime.now(UTC)

        # Единый контракт — platform_rules
        existing_rules = await repo.get_by_user_and_type(user_id, "platform_rules")
        if existing_rules:
            await self.session.execute(
                sa_update(Contract)
                .where(Contract.id == existing_rules.id)
                .values(
                    contract_status="signed",
                    signed_at=now,
                    signature_method="button_accept",
                )
            )
        else:
            await self.session.execute(
                insert(Contract).values(
                    user_id=user_id,
                    contract_type="platform_rules",
                    contract_status="signed",
                    signed_at=now,
                    signature_method="button_accept",
                    template_version=CONTRACT_TEMPLATE_VERSION,
                )
            )

        # Обратная совместимость: обновляем privacy_policy если он есть
        existing_privacy = await repo.get_by_user_and_type(user_id, "privacy_policy")
        if existing_privacy:
            await self.session.execute(
                sa_update(Contract)
                .where(Contract.id == existing_privacy.id)
                .values(
                    contract_status="signed",
                    signed_at=now,
                    signature_method="button_accept",
                )
            )

        await self.session.execute(
            sa_update(User)
            .where(User.id == user_id)
            .values(
                platform_rules_accepted_at=now,
                privacy_policy_accepted_at=now,
            )
        )
        await self.session.flush()

    async def get_user_contracts(
        self, user_id: int, contract_type: str | None = None
    ) -> list[Contract]:
        """Получить список договоров пользователя."""
        return await ContractRepo(self.session).list_by_user(user_id, contract_type)

    async def check_owner_contract(self, user_id: int) -> bool:
        """Проверить наличие подписанного договора владельца."""
        contract = await ContractRepo(self.session).get_by_user_and_type(user_id, "owner_service")
        return contract is not None and contract.contract_status == "signed"

    async def check_advertiser_can_pay(
        self, user_id: int, placement_request_id: int
    ) -> tuple[bool, Contract | None]:
        """
        Проверить, может ли рекламодатель оплатить размещение.

        Returns:
            (True, contract) если договор подписан, (False, contract) иначе.
            Если договора нет — создаёт новый.
        """
        repo = ContractRepo(self.session)
        contract = await repo.get_by_user_and_placement(user_id, placement_request_id)
        if contract and contract.contract_status == "signed":
            return (True, contract)
        if contract:
            return (False, contract)
        new_contract = await self.generate_contract(
            user_id, "advertiser_campaign", placement_request_id
        )
        return (False, new_contract)

    async def request_kep_version(self, contract_id: int, user_id: int, email: str) -> None:
        """Запросить КЭП-версию договора для ЮЛ/ИП."""
        result = await self.session.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one_or_none()
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        if contract.user_id != user_id:
            raise PermissionError("Contract does not belong to user")
        await ContractRepo(self.session).request_kep(contract_id, email)
        await self.session.flush()

    @staticmethod
    def needs_kep_warning(legal_status: str) -> bool:
        """Вернуть True для статусов, которым рекомендуется КЭП."""
        return legal_status in KEP_REQUIRED_STATUSES

    async def get_or_create_framework_contract(
        self, user_id: int, role: str
    ) -> tuple[Contract, bool]:
        """Получить существующий или создать новый рамочный договор рекламодателя.

        Returns:
            (contract, created) — created=False если договор уже существует.
        """
        existing = await ContractRepo(self.session).get_framework_contract(user_id, role)
        if existing:
            return (existing, False)
        contract = await self.generate_contract(user_id, "advertiser_framework")
        # Persist role on the contract row
        await self.session.execute(
            sa_update(Contract).where(Contract.id == contract.id).values(role=role)
        )
        await self.session.flush()
        contract.role = role
        return (contract, True)

    def _render_template(
        self,
        contract_type: str,
        profile: object | None,
        contract_id: int,
        platform_ctx: dict | None = None,
    ) -> str:
        """Отрендерить HTML шаблон договора."""
        legal_status = getattr(profile, "legal_status", None) if profile else None
        templates = _CONTRACT_TEMPLATE_MAP.get(contract_type, {})
        tpl_file = (
            templates.get(legal_status or "") or templates.get("_default") or PLATFORM_RULES_FILE
        )

        ctx: dict = {
            "legal_name": getattr(profile, "legal_name", "") or "",
            "inn": getattr(profile, "inn", "") or "",
            "address": getattr(profile, "address", "") or "",
            "yoomoney_wallet": getattr(profile, "yoomoney_wallet", "") or "",
            "contract_date": datetime.now(UTC).strftime("%d.%m.%Y"),
            "platform_name": "RekHarborBot",
            "contract_id": contract_id,
        }
        if platform_ctx:
            ctx.update({k: v for k, v in platform_ctx.items() if v is not None})

        if USE_JINJA2 and TEMPLATES_DIR.exists():
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
            )
            try:
                return env.get_template(tpl_file).render(**ctx)
            except Exception:
                pass

        # Fallback: plain HTML
        return (
            f"<html><body>"
            f"<h1>Договор №{contract_id}</h1>"
            f"<p>Дата: {ctx['contract_date']}</p>"
            f"<p>Сторона: {ctx['legal_name']}</p>"
            f"<p>ИНН: {ctx['inn']}</p>"
            f"</body></html>"
        )

    def _html_to_pdf(self, html: str, contract_id: int) -> Path | None:
        """Конвертировать HTML в PDF (если WeasyPrint доступен)."""
        output_path = CONTRACTS_OUTPUT_DIR / f"contract_{contract_id}.pdf"

        if USE_WEASYPRINT:
            try:
                weasyprint.HTML(string=html).write_pdf(str(output_path))  # type: ignore[name-defined]
                return output_path
            except Exception as e:
                logger.warning(f"PDF generation failed: {e}")
                return None
        else:
            # Save HTML as fallback
            html_path = CONTRACTS_OUTPUT_DIR / f"contract_{contract_id}.html"
            html_path.write_text(html, encoding="utf-8")
            return None  # no PDF available

    async def render_platform_rules(self) -> str:
        """Отрендерить HTML-текст Правил платформы (без привязки к пользователю).

        Используется на экране принятия правил для предпросмотра.
        """
        platform_ctx = await self._get_platform_ctx()
        ctx: dict = {
            "legal_name": "",
            "inn": "",
            "address": "",
            "yoomoney_wallet": "",
            "contract_date": datetime.now(UTC).strftime("%d.%m.%Y"),
            "platform_name": "RekHarborBot",
            "contract_id": 0,
        }
        ctx.update({k: v for k, v in platform_ctx.items() if v is not None})

        # CSS-переопределения для тёмной темы Mini App
        dark_mode_css = """
<style>
  @media screen {
    body { background: #1a1a2e !important; color: #e0e0e0 !important; }
    .box-info { background: #0d2137 !important; border-left-color: #64b5f6 !important; color: #bbdefb !important; }
    .box-warn { background: #2d1a00 !important; border-left-color: #ff9800 !important; color: #ffe0b2 !important; }
    .hl { background: #3d3d1a !important; color: #fff9c4 !important; }
    .consent { background: #1e1e30 !important; border-color: #555 !important; color: #e0e0e0 !important; }
    th { background: #2a2a3e !important; color: #e0e0e0 !important; border-color: #444 !important; }
    td { border-color: #444 !important; color: #e0e0e0 !important; }
    h2 { border-bottom-color: #444 !important; color: #ffffff !important; }
    h1, h3 { color: #ffffff !important; }
    p, li { color: #e0e0e0 !important; }
    .psub, .edate, .slabel { color: #888 !important; }
    .sline { border-bottom-color: #888 !important; }
  }
</style>
"""

        if USE_JINJA2 and TEMPLATES_DIR.exists():
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
            )
            try:
                html = env.get_template(PLATFORM_RULES_FILE).render(**ctx)
                # Вставляем dark_mode_css перед закрывающим </head>
                if "</head>" in html:
                    html = html.replace("</head>", f"  {dark_mode_css}\n</head>", 1)
                return html
            except Exception:
                logger.exception("Failed to render platform rules template")

        return (
            "<html><body>"
            "<h1>Правила платформы RekHarborBot</h1>"
            "<p>Текст правил временно недоступен. "
            "Обратитесь в поддержку для получения полной версии.</p>"
            "</body></html>"
        )
