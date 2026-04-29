"""Unit tests for `get_act_template`: resolver returns correct template
path per (party, legal_status) combination (Промт 15.11 / BL-040).
"""
from __future__ import annotations

import pytest

from src.core.services.act_service import (
    ACT_TEMPLATE_ADVERTISER,
    ACT_TEMPLATE_MAP_OWNER,
    ACT_TEMPLATE_PLATFORM,
    get_act_template,
)


def test_advertiser_party_returns_advertiser_template() -> None:
    assert get_act_template("advertiser") == ACT_TEMPLATE_ADVERTISER
    assert ACT_TEMPLATE_ADVERTISER == "acts/act_advertiser.html"


def test_platform_party_returns_placement_template() -> None:
    assert get_act_template("platform") == ACT_TEMPLATE_PLATFORM
    assert ACT_TEMPLATE_PLATFORM == "acts/act_placement.html"


@pytest.mark.parametrize(
    "legal_status,expected_template",
    [
        ("individual", "acts/act_owner_fl.html"),
        ("self_employed", "acts/act_owner_np.html"),
        ("individual_entrepreneur", "acts/act_owner_ie.html"),
        ("legal_entity", "acts/act_owner_le.html"),
    ],
)
def test_owner_party_returns_legal_status_specific_template(
    legal_status: str, expected_template: str
) -> None:
    assert get_act_template("owner", legal_status) == expected_template


def test_owner_party_without_legal_status_raises() -> None:
    with pytest.raises(ValueError, match="legal_status"):
        get_act_template("owner", None)


def test_owner_party_unknown_legal_status_raises() -> None:
    with pytest.raises(ValueError, match="not in ACT_TEMPLATE_MAP_OWNER"):
        get_act_template("owner", "unknown_status")


def test_unknown_party_raises() -> None:
    with pytest.raises(ValueError, match="Unknown party"):
        get_act_template("administrator")


def test_owner_template_map_covers_all_legal_status_enum_values() -> None:
    """Регрессия: ACT_TEMPLATE_MAP_OWNER должен покрывать все
    LegalStatus enum values из src/api/schemas/legal_profile.py.
    Если enum расширится — этот тест поймает gap.
    """
    from src.api.schemas.legal_profile import LegalStatus

    enum_values = {ls.value for ls in LegalStatus}
    map_keys = set(ACT_TEMPLATE_MAP_OWNER.keys())
    assert enum_values == map_keys, (
        f"ACT_TEMPLATE_MAP_OWNER mismatch: enum={enum_values}, map={map_keys}"
    )
