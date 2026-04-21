"""
LegalProfileService — управление юридическими профилями пользователей.
S2: валидация ИНН, расчёт налоговой нагрузки, контроль полноты профиля.
"""

import logging
from decimal import Decimal

from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.legal import INN_WEIGHTS_10, INN_WEIGHTS_12_1, INN_WEIGHTS_12_2, NDFL_RATE
from src.core.security.field_encryption import HashableEncryptedString
from src.core.services.fns_validation_service import validate_entity_documents
from src.db.models.legal_profile import LegalProfile
from src.db.models.user import User
from src.db.repositories.legal_profile_repo import LegalProfileRepo

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS_MAP: dict[str, dict] = {
    "legal_entity": {
        "fields": [
            "legal_name",
            "inn",
            "kpp",
            "ogrn",
            "address",
            "bank_name",
            "bank_account",
            "bank_bik",
            "bank_corr_account",
        ],
        "scans": ["inn", "company_doc"],
        "show_bank_details": True,
        "show_passport": False,
        "show_yoomoney": False,
        "tax_regime_required": False,
    },
    "individual_entrepreneur": {
        "fields": [
            "legal_name",
            "inn",
            "ogrnip",
            "address",
            "bank_name",
            "bank_account",
            "bank_bik",
            "bank_corr_account",
        ],
        "scans": ["inn"],
        "show_bank_details": True,
        "show_passport": False,
        "show_yoomoney": False,
        "tax_regime_required": True,
    },
    "self_employed": {
        "fields": ["legal_name", "inn", "yoomoney_wallet"],
        "scans": ["self_employed_cert"],
        "show_bank_details": False,
        "show_passport": False,
        "show_yoomoney": True,
        "tax_regime_required": False,
    },
    "individual": {
        "fields": [
            "legal_name",
            "passport_series",
            "passport_number",
            "passport_issued_by",
            "passport_issue_date",
        ],
        "scans": ["passport"],
        "show_bank_details": False,
        "show_passport": True,
        "show_yoomoney": False,
        "tax_regime_required": False,
    },
}

_KNOWN_LEGAL_STATUSES: frozenset[str] = frozenset(_REQUIRED_FIELDS_MAP.keys())


def _require_known_status(legal_status: str) -> None:
    if legal_status not in _KNOWN_LEGAL_STATUSES:
        raise ValueError(
            f"Unknown legal_status: {legal_status!r} "
            f"(known: {sorted(_KNOWN_LEGAL_STATUSES)})"
        )


def _validate_documents_for_status(legal_status: str, data: dict) -> None:
    """Ensure submitted documents match the declared legal_status.

    Skips validation for payloads that don't carry any of the relevant
    fields (partial updates of unrelated columns like bank_name).
    """
    relevant_keys = ("ogrn", "ogrnip", "passport_series", "passport_number")
    if not any(data.get(k) for k in relevant_keys):
        return
    ok, err = validate_entity_documents(
        legal_status,
        ogrn=data.get("ogrn"),
        ogrnip=data.get("ogrnip"),
        passport_series=data.get("passport_series"),
        passport_number=data.get("passport_number"),
    )
    if not ok:
        raise ValueError(err or "Документы не соответствуют статусу")


class LegalProfileService:
    """Сервис для управления юридическими профилями пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_profile(self, user_id: int, data: dict) -> LegalProfile:
        """Создать юридический профиль пользователя."""
        status = data.get("legal_status")
        if status is None:
            raise ValueError("legal_status is required")
        _require_known_status(status)
        _validate_documents_for_status(status, data)
        if status == "self_employed":
            data["tax_regime"] = "npd"
        if status == "individual":
            data["tax_regime"] = "ndfl"
        if data.get("inn"):
            data["inn_hash"] = HashableEncryptedString.hash_value(data["inn"])
        profile = await LegalProfileRepo(self.session).create(user_id=user_id, **data)
        await self.check_completeness(user_id)
        return profile

    async def update_profile(self, user_id: int, data: dict) -> LegalProfile:
        """Обновить юридический профиль пользователя."""
        # Only validate legal_status if the caller explicitly changes it;
        # partial updates that don't touch the status must still work.
        if "legal_status" in data and data["legal_status"] is not None:
            _require_known_status(data["legal_status"])
            _validate_documents_for_status(data["legal_status"], data)
        if data.get("inn"):
            data["inn_hash"] = HashableEncryptedString.hash_value(data["inn"])
        profile = await LegalProfileRepo(self.session).update(user_id=user_id, **data)
        await self.check_completeness(user_id)
        return profile

    async def upload_scan(self, user_id: int, scan_type: str, file_id: str) -> None:
        """Загрузить скан документа."""
        scan_field_map = {
            "inn": "inn_scan_file_id",
            "passport": "passport_scan_file_id",
            "self_employed_cert": "self_employed_cert_file_id",
            "company_doc": "company_doc_file_id",
        }
        if scan_type not in scan_field_map:
            raise ValueError(f"Unknown scan_type: {scan_type}")
        field_name = scan_field_map[scan_type]
        await LegalProfileRepo(self.session).update_scan(user_id, field_name, file_id)

    async def get_required_fields(self, legal_status: str) -> dict:
        """Вернуть список обязательных полей для данного правового статуса.

        Raises ValueError on unknown statuses — empty fallback used to
        silently mark any profile as "complete" (see 2026-04-21 audit).
        """
        _require_known_status(legal_status)
        return _REQUIRED_FIELDS_MAP[legal_status]

    async def check_completeness(self, user_id: int) -> bool:
        """Проверить полноту юридического профиля и обновить флаг у пользователя."""
        repo = LegalProfileRepo(self.session)
        profile = await repo.get_by_user_id(user_id)
        if not profile:
            return False

        required = await self.get_required_fields(profile.legal_status)
        is_complete = True
        for field in required["fields"]:
            value = getattr(profile, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                is_complete = False
                break

        await self.session.execute(
            sa_update(User).where(User.id == user_id).values(legal_status_completed=is_complete)
        )
        await self.session.flush()
        return is_complete

    @staticmethod
    def validate_inn(inn: str) -> tuple[bool, str]:
        """
        Валидировать ИНН (10 или 12 цифр).

        Returns:
            Кортеж (is_valid, inn_type) где inn_type — '10-digit', '12-digit' или 'invalid'.
        """
        inn = inn.strip()
        if not inn.isdigit():
            return (False, "invalid")
        if len(inn) == 10:
            weights = INN_WEIGHTS_10
            check = (sum(w * int(d) for w, d in zip(weights, inn, strict=False)) % 11) % 10
            return (check == int(inn[9]), "10-digit")
        elif len(inn) == 12:
            w1 = INN_WEIGHTS_12_1
            w2 = INN_WEIGHTS_12_2
            c1 = (sum(w * int(d) for w, d in zip(w1, inn, strict=False)) % 11) % 10
            c2 = (sum(w * int(d) for w, d in zip(w2, inn, strict=False)) % 11) % 10
            return (c1 == int(inn[10]) and c2 == int(inn[11]), "12-digit")
        else:
            return (False, "invalid")

    async def calculate_tax(self, user_id: int, gross_amount: Decimal) -> dict:
        """
        Рассчитать налоговую нагрузку на выплату.

        Returns:
            dict с ключами: gross, tax, net, tax_note.
        """
        profile = await LegalProfileRepo(self.session).get_by_user_id(user_id)
        if not profile:
            return {
                "gross": gross_amount,
                "tax": Decimal("0"),
                "net": gross_amount,
                "tax_note": "Заполните юридический профиль для расчёта налогов.",
            }

        status = profile.legal_status

        if status in ("legal_entity", "individual_entrepreneur"):
            return {
                "gross": gross_amount,
                "tax": Decimal("0"),
                "net": gross_amount,
                "tax_note": "Налог уплачивается вами самостоятельно.",
            }

        if status == "self_employed":
            return {
                "gross": gross_amount,
                "tax": Decimal("0"),
                "net": gross_amount,
                "tax_note": "НПД (6%) вы уплачиваете самостоятельно через «Мой налог».",
            }

        if status == "individual":
            ndfl = (gross_amount * NDFL_RATE).quantize(Decimal("0.01"))
            return {
                "gross": gross_amount,
                "tax": ndfl,
                "net": gross_amount - ndfl,
                "tax_note": f"НДФЛ 13% ({ndfl} ₽) будет удержан платформой.",
            }

        return {"gross": gross_amount, "tax": Decimal("0"), "net": gross_amount, "tax_note": ""}
