"""
EGRUL/EGRIP validation service — проверка юрлиц и ИП через ФНС.

Для MVP: валидация контрольных сумм ИНН и ОГРН.
Post-MVP: интеграция с API ФНС (npchk.nalog.ru).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_INN_DIGITS_ONLY = "ИНН должен содержать только цифры"
_INN_CHECKSUM_ERROR = "Неверная контрольная сумма ИНН"
_INN_LENGTH_ERROR = "ИНН должен быть 10 или 12 цифр"


class FNSValidationError:
    """Ошибка валидации."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message


class FNSValidationResult:
    """Результат валидации."""

    def __init__(
        self,
        is_valid: bool,
        entity_type: str | None = None,  # 'legal_entity' or 'individual_entrepreneur'
        inn: str | None = None,
        name: str | None = None,
        kpp: str | None = None,
        ogrn: str | None = None,
        status: str | None = None,  # 'active', 'liquidated', etc.
        errors: list[FNSValidationError] | None = None,
        warnings: list[str] | None = None,
    ):
        self.is_valid = is_valid
        self.entity_type = entity_type
        self.inn = inn
        self.name = name
        self.kpp = kpp
        self.ogrn = ogrn
        self.status = status
        self.errors = errors or []
        self.warnings = warnings or []


def validate_inn_checksum(inn: str) -> bool:
    """
    Проверить контрольную сумму ИНН.

    ИНН юрлица: 10 цифр (2 контрольные)
    ИНН физлица/ИП: 12 цифр (2 контрольные)

    Алгоритм: https://ru.wikipedia.org/wiki/Индивидуальный_номер_налогоплательщика
    """
    if not inn.isdigit():
        return False

    if len(inn) == 10:
        # Юрлицо — проверяем последнюю (10-ю) контрольную цифру
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        total = sum(int(inn[i]) * weights[i] for i in range(9))
        check_digit = (total % 11) % 10
        return check_digit == int(inn[9])

    if len(inn) == 12:
        # Физлицо/ИП — проверяем обе контрольные цифры (11-ю и 12-ю)
        weights1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        weights2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]

        total1 = sum(int(inn[i]) * weights1[i] for i in range(10))
        check1 = (total1 % 11) % 10
        if check1 != int(inn[10]):
            return False

        total2 = sum(int(inn[i]) * weights2[i] for i in range(11))
        check2 = (total2 % 11) % 10
        return check2 == int(inn[11])

    return False


def validate_ogrn_checksum(ogrn: str) -> bool:
    """
    Проверить контрольную сумму ОГРН (13 цифр) или ОГРНИП (15 цифр).

    Последняя цифра — остаток от деления первых N-1 цифр на 11 (или 13 для ОГРНИП).
    """
    if not ogrn.isdigit():
        return False

    if len(ogrn) == 13:
        # ОГРН юрлица
        remainder = int(ogrn[:12]) % 11
        check = remainder % 10
        return check == int(ogrn[12])

    if len(ogrn) == 15:
        # ОГРНИП
        remainder = int(ogrn[:14]) % 13
        check = remainder % 10
        return check == int(ogrn[14])

    return False


def validate_kpp_format(kpp: str) -> bool:
    """Проверить формат КПП (9 цифр)."""
    # Первые 4 цифры — код налогового органа (должен быть валидным)
    # Для MVP просто проверяем формат
    return kpp.isdigit() and len(kpp) == 9


def validate_legal_entity(inn: str, kpp: str | None = None, ogrn: str | None = None) -> FNSValidationResult:
    """
    Валидация данных юридического лица.

    Проверяет:
    - ИНН (10 цифр + контрольная сумма)
    - КПП (9 цифр, если указан)
    - ОГРН (13 цифр + контрольная сумма, если указан)
    """
    errors: list[FNSValidationError] = []
    warnings: list[str] = []

    # ИНН
    if not inn:
        errors.append(FNSValidationError("inn", "ИНН обязателен"))
        return FNSValidationResult(is_valid=False, errors=errors)

    if not inn.isdigit():
        errors.append(FNSValidationError("inn", _INN_DIGITS_ONLY))
        return FNSValidationResult(is_valid=False, errors=errors)

    if len(inn) == 10:
        if not validate_inn_checksum(inn):
            errors.append(FNSValidationError("inn", _INN_CHECKSUM_ERROR))
            return FNSValidationResult(is_valid=False, errors=errors)
        entity_type = "legal_entity"
    elif len(inn) == 12:
        warnings.append("ИНН из 12 цифр характерен для ИП/физлица, а не для ООО")
        entity_type = "individual_entrepreneur"
    else:
        errors.append(FNSValidationError("inn", _INN_LENGTH_ERROR))
        return FNSValidationResult(is_valid=False, errors=errors)

    # КПП
    if kpp and not validate_kpp_format(kpp):
        errors.append(FNSValidationError("kpp", "КПП должен быть 9 цифр"))

    # ОГРН
    if ogrn:
        if len(ogrn) != 13:
            errors.append(FNSValidationError("ogrn", "ОГРН должен быть 13 цифр"))
        elif not validate_ogrn_checksum(ogrn):
            errors.append(FNSValidationError("ogrn", "Неверная контрольная сумма ОГРН"))

    is_valid = len(errors) == 0

    return FNSValidationResult(
        is_valid=is_valid,
        entity_type=entity_type,
        inn=inn,
        kpp=kpp,
        ogrn=ogrn,
        status="format_validated",  # TODO: check via FNS API
        errors=errors,
        warnings=warnings,
    )


def validate_individual_entrepreneur(
    inn: str, ogrnip: str | None = None
) -> FNSValidationResult:
    """
    Валидация данных ИП.

    Проверяет:
    - ИНН (12 цифр + контрольная сумма)
    - ОГРНИП (15 цифр + контрольная сумма, если указан)
    """
    errors: list[FNSValidationError] = []
    warnings: list[str] = []

    # ИНН
    if not inn:
        errors.append(FNSValidationError("inn", "ИНН обязателен"))
        return FNSValidationResult(is_valid=False, errors=errors)

    if len(inn) not in (10, 12):
        errors.append(FNSValidationError("inn", _INN_LENGTH_ERROR))
        return FNSValidationResult(is_valid=False, errors=errors)

    if not validate_inn_checksum(inn):
        errors.append(FNSValidationError("inn", _INN_CHECKSUM_ERROR))
        return FNSValidationResult(is_valid=False, errors=errors)

    # ОГРНИП
    if ogrnip:
        if len(ogrnip) != 15:
            errors.append(FNSValidationError("ogrnip", "ОГРНИП должен быть 15 цифр"))
        elif not validate_ogrn_checksum(ogrnip):
            errors.append(FNSValidationError("ogrnip", "Неверная контрольная сумма ОГРНИП"))

    is_valid = len(errors) == 0

    return FNSValidationResult(
        is_valid=is_valid,
        entity_type="individual_entrepreneur",
        inn=inn,
        ogrn=ogrnip,
        status="format_validated",  # TODO: check via FNS API
        errors=errors,
        warnings=warnings,
    )


def validate_inn_type(inn: str) -> dict[str, Any]:
    """
    Быстрая проверка ИНН — определяет тип и валидность.

    Returns:
        dict с полями: valid, type, errors
    """
    if not inn or not inn.isdigit():
        return {"valid": False, "type": None, "errors": [_INN_DIGITS_ONLY]}

    if len(inn) == 10:
        valid = validate_inn_checksum(inn)
        return {
            "valid": valid,
            "type": "legal_entity",
            "errors": [] if valid else [_INN_CHECKSUM_ERROR],
        }

    if len(inn) == 12:
        valid = validate_inn_checksum(inn)
        return {
            "valid": valid,
            "type": "individual",
            "errors": [] if valid else [_INN_CHECKSUM_ERROR],
        }

    return {
        "valid": False,
        "type": None,
        "errors": [_INN_LENGTH_ERROR],
    }


def validate_entity_type_match(legal_status: str, inn: str) -> tuple[bool, str | None]:
    """
    Проверить что выбранный юридический статус соответствует типу ИНН.

    ИНН 10 цифр → только legal_entity (ООО)
    ИНН 12 цифр → individual, self_employed, individual_entrepreneur

    Returns:
        (is_valid, error_message)
    """
    if not inn or not inn.isdigit():
        return False, _INN_DIGITS_ONLY

    inn_type = None
    if len(inn) == 10:
        inn_type = "legal_entity"
    elif len(inn) == 12:
        inn_type = "individual"  # covers individual, self_employed, IE
    else:
        return False, _INN_LENGTH_ERROR

    # 10-значный ИНН не может быть ИП или физлицом
    if inn_type == "legal_entity" and legal_status != "legal_entity":
        return False, "10-значный ИНН характерен для юрлица (ООО/АО), а не для выбранного статуса"

    # 12-значный ИНН не может быть ООО
    if inn_type == "individual" and legal_status == "legal_entity":
        return False, "12-значный ИНН характерен для физлица/ИП, а не для юрлица (ООО/АО)"

    return True, None
