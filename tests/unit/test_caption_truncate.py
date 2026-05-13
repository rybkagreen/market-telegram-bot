"""Unit tests for caption truncate logic (BL-080 8d Option A)."""

import pytest

from src.core.services.publication_service import PublicationService
from src.db.models.placement_request import PlacementRequest
from src.utils.telegram_limits import TELEGRAM_CAPTION_LIMIT, truncate_ad_text


def _placement(
    *,
    erid: str | None = "ERID-XYZ-001",
    is_test: bool = False,
    ad_text: str = "Купите наш продукт!",
    advertiser_name: str | None = "ООО Тест",
    tracking_short_code: str | None = None,
) -> PlacementRequest:
    """Stub PlacementRequest with attributes _build_marked_text reads."""
    p = PlacementRequest()
    p.id = 42
    p.erid = erid
    p.is_test = is_test
    p.ad_text = ad_text
    p.tracking_short_code = tracking_short_code
    if advertiser_name is not None:
        p.advertiser_name = advertiser_name  # type: ignore[attr-defined]
    return p


class TestTruncateAdText:
    """Direct tests of truncate_ad_text helper."""

    def test_no_truncate_when_short(self) -> None:
        result = truncate_ad_text("Hello world", max_chars=100)
        assert result == "Hello world"

    def test_no_truncate_when_exactly_at_limit(self) -> None:
        text = "a" * 50
        result = truncate_ad_text(text, max_chars=50)
        assert result == text
        assert len(result) == 50

    def test_truncate_when_over_limit(self) -> None:
        text = "Hello world this is a longer message that needs trimming"
        result = truncate_ad_text(text, max_chars=20)
        assert len(result) <= 20
        assert result.endswith("…")

    def test_word_boundary_respected(self) -> None:
        text = "Hello wonderful amazing extraordinary content"
        result = truncate_ad_text(text, max_chars=20)
        assert result.endswith("…")
        body = result[:-1].rstrip()
        # Body must appear verbatim somewhere in source (no mid-word cut)
        assert body in text

    def test_hard_cut_when_single_word_too_long(self) -> None:
        text = "abcdefghijklmnop"
        result = truncate_ad_text(text, max_chars=10)
        assert result == "abcdefghi…"
        assert len(result) == 10

    def test_empty_string_returns_empty(self) -> None:
        assert truncate_ad_text("", max_chars=100) == ""

    def test_non_positive_budget_returns_empty(self) -> None:
        assert truncate_ad_text("hello", max_chars=0) == ""
        assert truncate_ad_text("hello", max_chars=-5) == ""

    def test_newline_treated_as_word_boundary(self) -> None:
        text = "First line\nSecond line\nThird line of content"
        result = truncate_ad_text(text, max_chars=20)
        assert result.endswith("…")
        body = result[:-1].rstrip()
        assert body in text


class TestBuildMarkedTextCaptionBudget:
    """End-to-end caption budget logic in _build_marked_text."""

    def test_no_truncate_short_text_with_media_caption_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Short ad_text → no truncate even with for_media_caption=True."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        text = PublicationService._build_marked_text(
            _placement(ad_text="Короткий текст"),
            for_media_caption=True,
        )
        assert text.startswith("Короткий текст\n\nРеклама.")
        assert "…" not in text
        assert len(text) <= TELEGRAM_CAPTION_LIMIT

    def test_truncate_long_text_for_media_caption(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Long ad_text → truncated; disclaimer preserved, total ≤ 1024."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        long_text = "Слово " * 300  # ~1800 chars
        text = PublicationService._build_marked_text(
            _placement(ad_text=long_text, erid="ERID-LONG-001"),
            for_media_caption=True,
        )
        assert len(text) <= TELEGRAM_CAPTION_LIMIT
        assert "Реклама. ООО Тест" in text
        assert "erid: ERID-LONG-001" in text
        assert "…" in text

    def test_tracking_url_in_budget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Composed text with tracking URL stays under 1024."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        long_text = "А" * 1500
        text = PublicationService._build_marked_text(
            _placement(
                ad_text=long_text,
                erid="ERID-TRK-001",
                tracking_short_code="abc123def456ghi7",
            ),
            for_media_caption=True,
        )
        assert len(text) <= TELEGRAM_CAPTION_LIMIT
        assert "🔗 " in text
        assert "Реклама. ООО Тест" in text
        assert "erid: ERID-TRK-001" in text

    def test_long_advertiser_name_reduces_budget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Longer disclaimer → less ad_text fits."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        short_name_text = PublicationService._build_marked_text(
            _placement(
                ad_text="А" * 2000,
                erid="ERID-001",
                advertiser_name="К",
            ),
            for_media_caption=True,
        )
        long_name_text = PublicationService._build_marked_text(
            _placement(
                ad_text="А" * 2000,
                erid="ERID-001",
                advertiser_name="К" * 100,
            ),
            for_media_caption=True,
        )
        assert len(short_name_text) <= TELEGRAM_CAPTION_LIMIT
        assert len(long_name_text) <= TELEGRAM_CAPTION_LIMIT
        short_ad_portion = short_name_text.split("\n\nРеклама.")[0]
        long_ad_portion = long_name_text.split("\n\nРеклама.")[0]
        assert len(short_ad_portion) > len(long_ad_portion)

    def test_text_only_post_no_truncate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """for_media_caption=False (text-only post) → no truncate even if over 1024."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        long_text = "А" * 2000  # over 1024 but under 4096
        text = PublicationService._build_marked_text(
            _placement(ad_text=long_text, erid="ERID-NOTRUNC-001"),
            for_media_caption=False,
        )
        assert text.startswith(long_text)
        assert "…" not in text

    def test_composed_exactly_at_caption_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ad_text sized so composed text = 1024 exactly → no truncate, no ellipsis."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        erid = "ERID-EXACT-001"
        name = "ООО Тест"
        disclaimer = f"\n\nРеклама. {name}\nerid: {erid}"
        ad_text = "А" * (TELEGRAM_CAPTION_LIMIT - len(disclaimer))
        text = PublicationService._build_marked_text(
            _placement(ad_text=ad_text, erid=erid, advertiser_name=name),
            for_media_caption=True,
        )
        assert len(text) == TELEGRAM_CAPTION_LIMIT
        assert "…" not in text
        assert text.startswith(ad_text)

    def test_tracking_pushes_over_limit_triggers_truncate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ad_text fits without tracking, but tracking_short_code adds chars → truncate kicks in."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        erid = "ERID-TRK-PUSH-001"
        name = "ООО Тест"
        disclaimer = f"\n\nРеклама. {name}\nerid: {erid}"
        # ad_text exactly fills budget when no tracking
        ad_text = "А " * ((TELEGRAM_CAPTION_LIMIT - len(disclaimer)) // 2)
        text_without_tracking = PublicationService._build_marked_text(
            _placement(ad_text=ad_text, erid=erid, advertiser_name=name),
            for_media_caption=True,
        )
        assert "…" not in text_without_tracking
        # Add tracking → composed would overflow → truncate kicks in
        text_with_tracking = PublicationService._build_marked_text(
            _placement(
                ad_text=ad_text,
                erid=erid,
                advertiser_name=name,
                tracking_short_code="abc123def456ghi7",
            ),
            for_media_caption=True,
        )
        assert len(text_with_tracking) <= TELEGRAM_CAPTION_LIMIT
        assert "…" in text_with_tracking
        assert "🔗 " in text_with_tracking

    def test_fallback_advertiser_name_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """advertiser_name=None → fallback 'Рекламодатель' used; budget accounts для fallback length."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "yandex")
        text = PublicationService._build_marked_text(
            _placement(
                ad_text="А" * 1500,
                erid="ERID-FALLBACK-001",
                advertiser_name=None,
            ),
            for_media_caption=True,
        )
        assert len(text) <= TELEGRAM_CAPTION_LIMIT
        assert "Реклама. Рекламодатель" in text
        assert "…" in text

    def test_stub_provider_no_erid_with_media_caption(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stub + no erid + media path → no disclaimer; for_media_caption still truncates if needed."""
        monkeypatch.setattr("src.core.services.publication_service.settings.ord_provider", "stub")
        long_text = "А" * 1500
        text = PublicationService._build_marked_text(
            _placement(ad_text=long_text, erid=None, is_test=False),
            for_media_caption=True,
        )
        assert len(text) <= TELEGRAM_CAPTION_LIMIT
        # No erid → no disclaimer; disclaimer overhead = 0 → ad_text truncated to fit 1024
        assert "Реклама" not in text
        assert "erid:" not in text
        assert "…" in text
