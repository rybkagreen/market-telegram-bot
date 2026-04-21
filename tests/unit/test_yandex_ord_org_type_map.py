"""Unit tests for static helpers in YandexOrdProvider — pure, no I/O.

Kept separate from `test_yandex_ord_provider.py` so the module-level
`pytest.mark.asyncio` in that file does not apply here."""

from __future__ import annotations

from src.core.services.yandex_ord_provider import (
    ORG_TYPE_MAP,
    YandexOrdProvider,
)


class TestOrgTypeMap:
    def test_legal_entity_maps_to_ul(self) -> None:
        assert ORG_TYPE_MAP["legal_entity"] == "ul"

    def test_individual_entrepreneur_maps_to_ip(self) -> None:
        assert ORG_TYPE_MAP["individual_entrepreneur"] == "ip"

    def test_self_employed_maps_to_fl(self) -> None:
        assert ORG_TYPE_MAP["self_employed"] == "fl"

    def test_individual_maps_to_fl(self) -> None:
        assert ORG_TYPE_MAP["individual"] == "fl"


class TestMapOrgType:
    def test_unknown_defaults_to_fl(self) -> None:
        assert YandexOrdProvider._map_org_type("something_unexpected") == "fl"

    def test_empty_defaults_to_fl(self) -> None:
        assert YandexOrdProvider._map_org_type("") == "fl"


class TestVatRate:
    def test_ul_is_22(self) -> None:
        assert YandexOrdProvider._determine_vat_rate("ul") == "22"

    def test_non_ul_is_100(self) -> None:
        for t in ("fl", "ip", "sp", "unknown"):
            assert YandexOrdProvider._determine_vat_rate(t) == "100"
