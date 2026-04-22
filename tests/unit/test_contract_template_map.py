"""Unit tests for the _CONTRACT_TEMPLATE_MAP: ensure the right HTML file is
chosen for each (contract_type, legal_status) pair and every declared file
exists on disk."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.services.contract_service import (
    _CONTRACT_TEMPLATE_MAP,
    TEMPLATES_DIR,
    ContractService,
)

ALL_OWNER_STATUSES = ["legal_entity", "individual_entrepreneur", "self_employed", "individual"]


class TestOwnerServiceMap:
    @pytest.mark.parametrize(
        ("legal_status", "expected_file"),
        [
            ("legal_entity", "owner_service_legal_entity.html"),
            ("individual_entrepreneur", "owner_service_ie.html"),
            ("self_employed", "owner_service_self_employed.html"),
            ("individual", "owner_service_individual.html"),
        ],
    )
    def test_template_file_matches_status(
        self, legal_status: str, expected_file: str
    ) -> None:
        assert _CONTRACT_TEMPLATE_MAP["owner_service"][legal_status] == expected_file

    @pytest.mark.parametrize("legal_status", ALL_OWNER_STATUSES)
    def test_template_file_exists_on_disk(self, legal_status: str) -> None:
        file_name = _CONTRACT_TEMPLATE_MAP["owner_service"][legal_status]
        assert (TEMPLATES_DIR / file_name).is_file(), (
            f"Owner-service template for {legal_status} missing: {file_name}"
        )


class TestAdvertiserMap:
    def test_advertiser_campaign_has_default(self) -> None:
        assert _CONTRACT_TEMPLATE_MAP["advertiser_campaign"]["_default"] == (
            "advertiser_campaign.html"
        )
        assert (TEMPLATES_DIR / "advertiser_campaign.html").is_file()

    def test_advertiser_framework_reuses_campaign_template(self) -> None:
        # Framework contracts reuse the campaign template via _default
        assert _CONTRACT_TEMPLATE_MAP["advertiser_framework"]["_default"] == (
            "advertiser_campaign.html"
        )


class TestPlatformRulesMap:
    def test_platform_rules_file(self) -> None:
        assert _CONTRACT_TEMPLATE_MAP["platform_rules"]["_default"] == "platform_rules.html"
        assert (TEMPLATES_DIR / "platform_rules.html").is_file()

    def test_privacy_policy_shares_platform_rules(self) -> None:
        """privacy_policy reuses the same HTML per the single-contract model."""
        assert _CONTRACT_TEMPLATE_MAP["privacy_policy"]["_default"] == "platform_rules.html"


class TestStructuralInvariants:
    def test_no_typo_contract_types(self) -> None:
        expected = {
            "owner_service",
            "advertiser_campaign",
            "advertiser_framework",
            "platform_rules",
            "privacy_policy",
        }
        assert expected.issubset(set(_CONTRACT_TEMPLATE_MAP.keys()))

    def test_owner_service_covers_all_4_statuses(self) -> None:
        """Regression guard: each legal_status must resolve to a template.

        If a new LegalStatus enum value is added, this test starts failing
        until the map is updated — prevents silent fall-through to _default.
        """
        mapping = _CONTRACT_TEMPLATE_MAP["owner_service"]
        for status in ALL_OWNER_STATUSES:
            assert status in mapping, f"owner_service map missing entry for {status!r}"

    def test_every_referenced_file_exists(self) -> None:
        """All template files referenced by the map must exist on disk."""
        for group in _CONTRACT_TEMPLATE_MAP.values():
            for file_name in group.values():
                path: Path = TEMPLATES_DIR / file_name
                assert path.is_file(), f"Template not found on disk: {path}"


class TestNeedsKepWarning:
    @pytest.mark.parametrize("status", ["legal_entity", "individual_entrepreneur"])
    def test_requires_kep_for_b2b(self, status: str) -> None:
        assert ContractService.needs_kep_warning(status) is True

    @pytest.mark.parametrize("status", ["self_employed", "individual", "unknown", ""])
    def test_does_not_require_kep_otherwise(self, status: str) -> None:
        assert ContractService.needs_kep_warning(status) is False
