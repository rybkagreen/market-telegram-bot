"""Unit tests for FNS validation service (INN/OGRN/KPP checksums + entity type match)
and the static `LegalProfileService.validate_inn` classifier."""

from __future__ import annotations

import pytest

from src.core.services.fns_validation_service import (
    validate_entity_documents,
    validate_entity_type_match,
    validate_individual_entrepreneur,
    validate_inn_checksum,
    validate_inn_type,
    validate_kpp_format,
    validate_legal_entity,
    validate_ogrn_checksum,
)
from tests.conftest import (
    VALID_INN10,
    VALID_INN12,
    VALID_KPP,
    VALID_OGRN,
    VALID_OGRNIP,
)

# ────────────────────────────────────────────
# INN checksum
# ────────────────────────────────────────────


class TestInnChecksum:
    def test_valid_10_digit(self) -> None:
        assert validate_inn_checksum(VALID_INN10) is True

    def test_valid_12_digit(self) -> None:
        assert validate_inn_checksum(VALID_INN12) is True

    def test_invalid_checksum_10(self) -> None:
        # Change the last digit so the checksum fails
        broken = VALID_INN10[:-1] + ("0" if VALID_INN10[-1] != "0" else "1")
        assert validate_inn_checksum(broken) is False

    def test_invalid_checksum_12(self) -> None:
        broken = VALID_INN12[:-1] + ("0" if VALID_INN12[-1] != "0" else "1")
        assert validate_inn_checksum(broken) is False

    def test_non_numeric(self) -> None:
        assert validate_inn_checksum("770708389X") is False

    def test_empty(self) -> None:
        assert validate_inn_checksum("") is False

    @pytest.mark.parametrize("length", [0, 1, 5, 9, 11, 13, 20])
    def test_wrong_length(self, length: int) -> None:
        assert validate_inn_checksum("1" * length) is False


# ────────────────────────────────────────────
# OGRN / OGRNIP checksum
# ────────────────────────────────────────────


class TestOgrnChecksum:
    def test_valid_ogrn_13(self) -> None:
        assert validate_ogrn_checksum(VALID_OGRN) is True

    def test_valid_ogrnip_15(self) -> None:
        assert validate_ogrn_checksum(VALID_OGRNIP) is True

    def test_invalid_ogrn_checksum(self) -> None:
        broken = VALID_OGRN[:-1] + ("0" if VALID_OGRN[-1] != "0" else "1")
        assert validate_ogrn_checksum(broken) is False

    def test_invalid_ogrnip_checksum(self) -> None:
        broken = VALID_OGRNIP[:-1] + ("0" if VALID_OGRNIP[-1] != "0" else "1")
        assert validate_ogrn_checksum(broken) is False

    def test_non_numeric(self) -> None:
        assert validate_ogrn_checksum("102770013A19") is False

    @pytest.mark.parametrize("length", [0, 12, 14, 16])
    def test_wrong_length(self, length: int) -> None:
        assert validate_ogrn_checksum("1" * length) is False


# ────────────────────────────────────────────
# KPP format
# ────────────────────────────────────────────


class TestKppFormat:
    def test_valid(self) -> None:
        assert validate_kpp_format(VALID_KPP) is True

    def test_wrong_length(self) -> None:
        assert validate_kpp_format("12345") is False
        assert validate_kpp_format("1234567890") is False

    def test_non_numeric(self) -> None:
        assert validate_kpp_format("77070100X") is False


# ────────────────────────────────────────────
# validate_legal_entity / _individual_entrepreneur
# ────────────────────────────────────────────


class TestValidateLegalEntity:
    def test_valid_with_kpp_and_ogrn(self) -> None:
        result = validate_legal_entity(VALID_INN10, kpp=VALID_KPP, ogrn=VALID_OGRN)
        assert result.is_valid is True
        assert result.entity_type == "legal_entity"
        assert result.errors == []

    def test_missing_inn(self) -> None:
        result = validate_legal_entity("", kpp=VALID_KPP, ogrn=VALID_OGRN)
        assert result.is_valid is False
        assert any(e.field == "inn" for e in result.errors)

    def test_invalid_kpp(self) -> None:
        result = validate_legal_entity(VALID_INN10, kpp="BAD", ogrn=VALID_OGRN)
        assert result.is_valid is False
        assert any(e.field == "kpp" for e in result.errors)

    def test_invalid_ogrn(self) -> None:
        result = validate_legal_entity(VALID_INN10, kpp=VALID_KPP, ogrn="1234567890123")
        assert result.is_valid is False
        assert any(e.field == "ogrn" for e in result.errors)

    def test_warning_on_12_digit_inn(self) -> None:
        result = validate_legal_entity(VALID_INN12)
        # 12-digit INN still validates (for IP), but yields a warning
        assert result.entity_type == "individual_entrepreneur"
        assert any("12 цифр" in w for w in result.warnings)


class TestValidateIndividualEntrepreneur:
    def test_valid(self) -> None:
        result = validate_individual_entrepreneur(VALID_INN12, ogrnip=VALID_OGRNIP)
        assert result.is_valid is True
        assert result.entity_type == "individual_entrepreneur"

    def test_invalid_ogrnip(self) -> None:
        result = validate_individual_entrepreneur(VALID_INN12, ogrnip="304500116000999")
        assert result.is_valid is False
        assert any(e.field == "ogrnip" for e in result.errors)


# ────────────────────────────────────────────
# validate_inn_type (quick classifier)
# ────────────────────────────────────────────


class TestValidateInnType:
    def test_10_digit_legal_entity(self) -> None:
        result = validate_inn_type(VALID_INN10)
        assert result["valid"] is True
        assert result["type"] == "legal_entity"

    def test_12_digit_individual(self) -> None:
        result = validate_inn_type(VALID_INN12)
        assert result["valid"] is True
        assert result["type"] == "individual"

    def test_invalid_length(self) -> None:
        result = validate_inn_type("12345")
        assert result["valid"] is False
        assert result["type"] is None


# ────────────────────────────────────────────
# validate_entity_type_match — ключевой риск, помеченный пользователем
# ────────────────────────────────────────────


class TestValidateEntityTypeMatch:
    """Матрица соответствия legal_status ↔ длина ИНН."""

    @pytest.mark.parametrize(
        ("legal_status", "inn", "expected_ok"),
        [
            # legal_entity — только 10-значный
            ("legal_entity", VALID_INN10, True),
            ("legal_entity", VALID_INN12, False),
            # individual_entrepreneur — 12-значный
            ("individual_entrepreneur", VALID_INN12, True),
            ("individual_entrepreneur", VALID_INN10, False),
            # self_employed — 12-значный
            ("self_employed", VALID_INN12, True),
            ("self_employed", VALID_INN10, False),
            # individual — 12-значный
            ("individual", VALID_INN12, True),
            ("individual", VALID_INN10, False),
        ],
    )
    def test_matrix(self, legal_status: str, inn: str, expected_ok: bool) -> None:
        ok, err = validate_entity_type_match(legal_status, inn)
        assert ok is expected_ok
        if not expected_ok:
            assert err is not None and err.strip() != ""

    def test_non_numeric(self) -> None:
        ok, err = validate_entity_type_match("legal_entity", "77070X3893")
        assert ok is False
        assert err is not None

    def test_wrong_length(self) -> None:
        ok, err = validate_entity_type_match("legal_entity", "12345")
        assert ok is False
        assert err is not None

    # The historical "self_employed + OGRNIP" gap lives in
    # `TestValidateEntityDocuments` below — INN-length matching alone is
    # correctly permissive for 12-digit INN; document-level validation is
    # the layer that rejects the combination.


# ────────────────────────────────────────────
# validate_entity_documents — закрывает пре-лонч зазор №2
# ────────────────────────────────────────────


class TestValidateEntityDocuments:
    """Матрица документов vs статус. Заменяет xfail'нутый сигнальный тест."""

    # (legal_status, ogrn, ogrnip, passport_series, passport_number, expected_ok)
    MATRIX = [
        # legal_entity — нужен OGRN, прочее запрещено
        ("legal_entity", VALID_OGRN, None, None, None, True),
        ("legal_entity", VALID_OGRN, VALID_OGRNIP, None, None, False),
        ("legal_entity", None, None, None, None, False),  # no OGRN
        ("legal_entity", VALID_OGRN, None, "4500", "123456", False),  # passport forbidden
        # individual_entrepreneur — нужен OGRNIP, прочее запрещено
        ("individual_entrepreneur", None, VALID_OGRNIP, None, None, True),
        ("individual_entrepreneur", VALID_OGRN, VALID_OGRNIP, None, None, False),
        ("individual_entrepreneur", None, None, None, None, False),
        ("individual_entrepreneur", None, VALID_OGRNIP, "4500", "123456", False),
        # self_employed — OGRN / OGRNIP запрещены
        ("self_employed", None, None, None, None, True),
        ("self_employed", None, VALID_OGRNIP, None, None, False),  # the key gap
        ("self_employed", VALID_OGRN, None, None, None, False),
        # individual — нужен паспорт, OGRN/OGRNIP запрещены
        ("individual", None, None, "4500", "123456", True),
        ("individual", None, None, None, None, False),
        ("individual", None, VALID_OGRNIP, "4500", "123456", False),
        ("individual", VALID_OGRN, None, "4500", "123456", False),
    ]

    @pytest.mark.parametrize(
        ("status", "ogrn", "ogrnip", "passport_series", "passport_number", "expected_ok"),
        MATRIX,
    )
    def test_matrix(
        self,
        status: str,
        ogrn: str | None,
        ogrnip: str | None,
        passport_series: str | None,
        passport_number: str | None,
        expected_ok: bool,
    ) -> None:
        ok, err = validate_entity_documents(
            status,
            ogrn=ogrn,
            ogrnip=ogrnip,
            passport_series=passport_series,
            passport_number=passport_number,
        )
        assert ok is expected_ok
        if not expected_ok:
            assert err is not None and err.strip() != ""

    def test_self_employed_with_ogrnip_is_rejected(self) -> None:
        """Regression for the 2026-04-21 xfail gap: self_employed + OGRNIP → reject."""
        ok, err = validate_entity_documents("self_employed", ogrnip=VALID_OGRNIP)
        assert ok is False
        assert err is not None and "ОГРНИП" in err

    def test_empty_strings_treated_as_absent(self) -> None:
        # legal_entity without OGRN (passed as empty string) must fail
        ok, _ = validate_entity_documents("legal_entity", ogrn="")
        assert ok is False

    def test_unknown_status_passes_through(self) -> None:
        # This function does not validate the enum — that's LegalProfileService's job
        ok, _ = validate_entity_documents("foobar", ogrn=VALID_OGRN)
        assert ok is True


# ────────────────────────────────────────────
# LegalProfileService.validate_inn (static classifier)
# ────────────────────────────────────────────


class TestLegalProfileServiceValidateInn:
    def test_valid_10(self) -> None:
        from src.core.services.legal_profile_service import LegalProfileService

        ok, kind = LegalProfileService.validate_inn(VALID_INN10)
        assert ok is True
        assert kind == "10-digit"

    def test_valid_12(self) -> None:
        from src.core.services.legal_profile_service import LegalProfileService

        ok, kind = LegalProfileService.validate_inn(VALID_INN12)
        assert ok is True
        assert kind == "12-digit"

    def test_invalid(self) -> None:
        from src.core.services.legal_profile_service import LegalProfileService

        ok, kind = LegalProfileService.validate_inn("1234")
        assert ok is False
        assert kind == "invalid"

    def test_non_numeric(self) -> None:
        from src.core.services.legal_profile_service import LegalProfileService

        ok, kind = LegalProfileService.validate_inn("7707X83893")
        assert ok is False
        assert kind == "invalid"
