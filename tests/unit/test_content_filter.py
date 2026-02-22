"""
Тесты для Content Filter.
"""

import pytest

from src.utils.content_filter.filter import ContentFilter, FilterResult


class TestRegexCheck:
    """Тесты regex проверки (Уровень 1)."""

    @pytest.fixture
    def content_filter(self) -> ContentFilter:
        """Создать ContentFilter."""
        return ContentFilter()

    @pytest.mark.parametrize(
        "text,should_block",
        [
            ("Купить наркотики в Москве", True),
            ("Героин амфетамин закладка", True),
            ("Взрывчатка для джихада", True),
            ("Купить автомат оружие", True),
            ("Порно эротика 18+", True),
            ("Лохотрон пирамида обнал", True),
            ("Суицид как покончить с собой", True),
            ("Нацист экстремизм", True),
            ("Казино ставки букмекер", True),
            ("Привет как дела", False),
            ("Куплю книгу в хорошем состоянии", False),
            ("Реклама чата про программирование", False),
        ],
    )
    def test_regex_check_categories(
        self,
        content_filter: ContentFilter,
        text: str,
        should_block: bool,
    ) -> None:
        """Проверка блокировки по категориям."""
        result = content_filter._regex_check(text)
        if should_block:
            assert result.score > 0.3
        else:
            assert result.score <= 0.3


class TestMorphCheck:
    """Тесты морфологической проверки (Уровень 2)."""

    @pytest.fixture
    def content_filter(self) -> ContentFilter:
        """Создать ContentFilter."""
        return ContentFilter()

    @pytest.mark.parametrize(
        "text,should_block",
        [
            ("наркотиках", True),  # Разные словоформы
            ("наркотикам", True),
            ("наркотиками", True),
            ("взрывчатку", True),
            ("оружиям", True),
            ("казиношке", True),
            ("нормальный текст", False),
            ("привет друзья", False),
        ],
    )
    def test_morph_check_word_forms(
        self,
        content_filter: ContentFilter,
        text: str,
        should_block: bool,
    ) -> None:
        """Проверка блокировки словоформ."""
        result = content_filter._morph_check(text)
        if should_block:
            assert result.score > 0
        else:
            assert result.score == 0


class TestContentFilter:
    """Интеграционные тесты ContentFilter."""

    @pytest.fixture
    def content_filter(self) -> ContentFilter:
        """Создать ContentFilter."""
        return ContentFilter()

    def test_check_clean_text(self, content_filter: ContentFilter) -> None:
        """Проверка чистого текста."""
        result = content_filter.check("Привет! Как твои дела?")
        assert result.passed is True
        assert result.score == 0.0
        assert len(result.categories) == 0

    def test_check_blocked_text(self, content_filter: ContentFilter) -> None:
        """Проверка заблокированного текста."""
        result = content_filter.check("Купить наркотики закладку")
        assert result.passed is False
        assert result.score > 0.3
        assert "drugs" in result.categories

    def test_check_mixed_text(self, content_filter: ContentFilter) -> None:
        """Проверка смешанного текста."""
        result = content_filter.check(
            "Привет! Это реклама казино и ставок на спорт, купите наркотики"
        )
        assert result.passed is False
        assert "gambling" in result.categories
        assert "drugs" in result.categories

    def test_check_empty_text(self, content_filter: ContentFilter) -> None:
        """Проверка пустого текста."""
        result = content_filter.check("")
        assert result.passed is True
        assert result.score == 0.0

    def test_check_short_text(self, content_filter: ContentFilter) -> None:
        """Проверка короткого текста."""
        result = content_filter.check("Привет")
        assert result.passed is True
        assert result.score == 0.0

    def test_check_long_text(self, content_filter: ContentFilter) -> None:
        """Проверка длинного текста."""
        long_text = "Привет! " * 1000
        result = content_filter.check(long_text)
        assert result.passed is True
        assert result.score == 0.0

    def test_check_case_insensitive(
        self, content_filter: ContentFilter
    ) -> None:
        """Проверка регистронезависимости."""
        result1 = content_filter.check("НАРКОТИКИ")
        result2 = content_filter.check("наркотики")
        assert result1.score == result2.score

    def test_merge_categories(self, content_filter: ContentFilter) -> None:
        """Проверка объединения категорий."""
        categories = content_filter._merge_categories(
            ["drugs", "weapons"],
            ["adult", "drugs"],
            ["fraud"],
        )
        assert len(categories) == 4
        assert "drugs" in categories
        assert "weapons" in categories
        assert "adult" in categories
        assert "fraud" in categories


class TestFilterResult:
    """Тесты FilterResult dataclass."""

    def test_filter_result_default(self) -> None:
        """Проверка значений по умолчанию."""
        result = FilterResult(
            passed=True,
            score=0.0,
        )
        assert result.passed is True
        assert result.score == 0.0
        assert len(result.categories) == 0
        assert len(result.flagged_fragments) == 0

    def test_filter_result_custom(self) -> None:
        """Проверка кастомных значений."""
        result = FilterResult(
            passed=False,
            score=0.8,
            categories=["drugs", "weapons"],
            flagged_fragments=["наркотики", "автомат"],
        )
        assert result.passed is False
        assert result.score == 0.8
        assert len(result.categories) == 2
        assert len(result.flagged_fragments) == 2
