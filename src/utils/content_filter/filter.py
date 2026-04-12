"""
Content Filter — 3-уровневая система проверки контента.

Уровни:
1. regex_check — быстрая проверка по стоп-словам (< 1 мс)
2. morph_check — проверка нормализованных словоформ (pymorphy3)
3. llm_check — LLM анализ через Mistral AI (mistral-medium-latest)

8 заблокированных категорий:
- drugs, terrorism, weapons, adult
- fraud, suicide, extremism, gambling
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pymorphy3

    MORPH_AVAILABLE = True
except ImportError:
    pymorphy3 = None
    MORPH_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Результат проверки контента."""

    passed: bool  # Прошел ли проверку
    score: float  # Общая оценка (0.0 - 1.0)
    categories: list[str] = field(default_factory=list)  # Категории нарушений
    flagged_fragments: list[str] = field(default_factory=list)  # Помеченные фрагменты
    level1_score: float = 0.0  # Оценка уровня 1 (regex)
    level2_score: float = 0.0  # Оценка уровня 2 (morph)
    level3_score: float = 0.0  # Оценка уровня 3 (LLM)
    llm_analysis: str | None = None  # Результат LLM анализа


# Пороги для перехода между уровнями
LEVEL1_THRESHOLD = 0.1  # Если score > 0.1, переходим на уровень 2 (было 0.2)
LEVEL2_THRESHOLD = 0.15  # Если score > 0.15, блокируем (было 0.5) — одно ключевое слово = 0.2
LEVEL3_THRESHOLD = 0.7  # Если LLM score > 0.7, контент блокируется


class ContentFilter:
    """
    3-уровневый фильтр контента.

    Использование:
        filter = ContentFilter()
        result = filter.check("Текст для проверки")
        if not result.passed:
            print(f"Заблокировано: {result.categories}")
    """

    def __init__(self, stopwords_path: str | None = None) -> None:
        """
        Инициализация фильтра.

        Args:
            stopwords_path: Путь к JSON файлу со стоп-словами.
        """
        if stopwords_path is None:
            stopwords_path = str(Path(__file__).parent / "stopwords_ru.json")

        self._stopwords: dict[str, list[str]] = {}
        self._regex_patterns: dict[str, list[re.Pattern[str]]] = {}
        self._morph = pymorphy3.MorphAnalyzer() if MORPH_AVAILABLE else None

        self._load_stopwords(stopwords_path)
        self._compile_patterns()

    def _load_stopwords(self, path: str) -> None:
        """Загрузить стоп-слова из JSON файла."""
        try:
            with open(path, encoding="utf-8") as f:
                self._stopwords = json.load(f)
            logger.info("Loaded %d categories from %s", len(self._stopwords), path)
        except FileNotFoundError:
            logger.critical("Stopwords file not found: %s — content filter DISABLED", path)
            import sentry_sdk

            sentry_sdk.capture_exception()
            self._stopwords = {}
        except json.JSONDecodeError as e:
            logger.critical("Invalid JSON in stopwords file %s: %s", path, e)
            import sentry_sdk

            sentry_sdk.capture_exception()
            self._stopwords = {}
        except Exception as e:
            logger.critical("Unexpected error loading stopwords: %s", e)
            import sentry_sdk

            sentry_sdk.capture_exception()
            self._stopwords = {}

    def _compile_patterns(self) -> None:
        """Скомпилировать regex паттерны для каждой категории."""
        for category, words in self._stopwords.items():
            patterns = []
            for word in words:
                # Пропускаем пустые слова
                if not word or not word.strip():
                    continue
                word = word.strip()
                # Экранируем специальные символы
                escaped = re.escape(word)
                # Удаляем trailing regex квантификаторы (*, +, ?) после экранирования
                escaped = re.sub(r"([\\][*+?])+$", "", escaped)
                # Пропускаем если после обработки пусто
                if not escaped:
                    continue
                # Паттерн ищет слово в любой форме (часть слова)
                # Используем (?<!\w) вместо \b? так как к \b нельзя применять ?
                try:
                    pattern = re.compile(rf"(?<!\w){escaped}\w*", re.IGNORECASE | re.UNICODE)
                    patterns.append(pattern)
                except re.error:
                    # Пропускаем слова которые не могут быть скомпилированы
                    continue
            self._regex_patterns[category] = patterns

    async def check(self, text: str) -> FilterResult:
        """
        Проверить текст на запрещенный контент.

        Args:
            text: Текст для проверки.

        Returns:
            FilterResult с результатами проверки.
        """
        if not text or not text.strip():
            return FilterResult(
                passed=True,
                score=0.0,
            )

        # Уровень 1: Regex проверка
        level1_result = self._regex_check(text)

        if level1_result.score < LEVEL1_THRESHOLD:
            # Чистый текст, не требуется дальнейшая проверка
            return FilterResult(
                passed=True,
                score=level1_result.score,
            )

        # Уровень 2: Morph проверка
        level2_result = self._morph_check(text)
        combined_score = max(level1_result.score, level2_result.score)

        if combined_score < LEVEL2_THRESHOLD:
            # Низкий риск, не требуется LLM
            # Блокируем если есть запрещённые категории независимо от score
            has_blocked_category = len(level2_result.categories) > 0
            return FilterResult(
                passed=not has_blocked_category and combined_score < LEVEL3_THRESHOLD,
                score=combined_score,
                categories=level2_result.categories,
                flagged_fragments=level2_result.flagged_fragments,
                level1_score=level1_result.score,
                level2_score=level2_result.score,
            )

        # Уровень 3: LLM проверка (включено с таймаутом)
        from src.config.settings import settings

        if settings.content_filter_l3_enabled:
            try:
                # Асинхронный вызов с таймаутом
                level3_result = await self._llm_check_async(
                    text,
                    timeout=settings.content_filter_l3_timeout,
                )
                final_score = max(combined_score, level3_result.score)

                return FilterResult(
                    passed=final_score < LEVEL3_THRESHOLD,
                    score=final_score,
                    categories=self._merge_categories(
                        level1_result.categories,
                        level2_result.categories,
                        level3_result.categories,
                    ),
                    flagged_fragments=self._merge_fragments(
                        level1_result.flagged_fragments,
                        level2_result.flagged_fragments,
                    ),
                    level1_score=level1_result.score,
                    level2_score=level2_result.score,
                    level3_score=level3_result.score,
                    llm_analysis=level3_result.llm_analysis,
                )
            except TimeoutError:
                logger.warning(
                    "Content filter L3 timeout (%ds), failing open for placement",
                    settings.content_filter_l3_timeout,
                )
                import sentry_sdk

                sentry_sdk.capture_exception()
                # При таймауте — пропускаем (fail open)
            except Exception as e:
                logger.error("Content filter L3 error: %s", e)
                import sentry_sdk

                sentry_sdk.capture_exception()
                # При ошибке — пропускаем (fail open)

        # Если L3 отключен или ошибка — используем только уровень 2
        final_score = combined_score

        return FilterResult(
            passed=final_score < LEVEL3_THRESHOLD,
            score=final_score,
            categories=self._merge_categories(
                level1_result.categories,
                level2_result.categories,
            ),
            flagged_fragments=self._merge_fragments(
                level1_result.flagged_fragments,
                level2_result.flagged_fragments,
            ),
            level1_score=level1_result.score,
            level2_score=level2_result.score,
        )

    def _regex_check(self, text: str) -> FilterResult:
        """
        Уровень 1: Быстрая regex проверка.

        Args:
            text: Текст для проверки.

        Returns:
            FilterResult с результатами.
        """
        categories: list[str] = []
        flagged: list[str] = []
        total_matches = 0

        text_lower = text.lower()

        for category, patterns in self._regex_patterns.items():
            category_matches = 0
            for pattern in patterns:
                matches = pattern.findall(text_lower)
                if matches:
                    category_matches += len(matches)
                    flagged.extend(matches[:3])  # Ограничиваем количество фрагментов

            if category_matches > 0:
                categories.append(category)
                total_matches += category_matches

        # Вычисляем score на основе количества совпадений
        # Нормализуем: 1 совпадение = 0.1, 5+ = 1.0
        score = min(1.0, total_matches / 5.0)

        return FilterResult(
            passed=score < LEVEL3_THRESHOLD,
            score=score,
            categories=categories,
            flagged_fragments=list(set(flagged))[:10],
        )

    def _normalize_words(self, words: list[str]) -> list[str]:
        """Return the normal (lemma) form of each word using pymorphy3."""
        normalized: list[str] = []
        for word in words:
            try:
                parsed = self._morph.parse(word)[0]  # type: ignore[union-attr]
                normalized.append(parsed.normal_form)
            except Exception:
                normalized.append(word)
        return normalized

    def _morph_category_matches(
        self,
        words: list[str],
        normalized_words: list[str],
    ) -> tuple[list[str], list[str]]:
        """
        Match normalized words against stopword categories.

        Returns (categories, flagged_words).
        """
        categories: list[str] = []
        flagged: list[str] = []
        for category, stopwords in self._stopwords.items():
            category_matches: list[str] = []
            for i, norm_word in enumerate(normalized_words):
                for stopword in stopwords:
                    if norm_word == stopword or (len(stopword) > 3 and stopword in norm_word):
                        category_matches.append(words[i])
                        break
            if category_matches:
                categories.append(category)
                flagged.extend(category_matches[:3])
        return categories, flagged

    def _morph_check(self, text: str) -> FilterResult:
        """
        Уровень 2: Проверка с нормализацией словоформ.

        Args:
            text: Текст для проверки.

        Returns:
            FilterResult с результатами.
        """
        if not MORPH_AVAILABLE or self._morph is None:
            return FilterResult(passed=True, score=0.0)

        words = re.findall(r"\w+", text.lower())
        normalized_words = self._normalize_words(words)
        categories, flagged = self._morph_category_matches(words, normalized_words)

        score = min(1.0, len(categories) * 0.2 + len(flagged) * 0.05)

        return FilterResult(
            passed=score < LEVEL3_THRESHOLD,
            score=score,
            categories=list(set(categories)),
            flagged_fragments=list(set(flagged))[:10],
        )

    def _llm_check(self, text: str) -> FilterResult:
        """
        Уровень 3: LLM проверка через Mistral AI.
        Синхронная версия (для Celery).

        Args:
            text: Текст для проверки.

        Returns:
            FilterResult с результатами.
        """
        from src.core.services.mistral_ai_service import mistral_ai_service

        try:
            # Используем Mistral для модерации (синхронно для Celery)
            result = asyncio.run(mistral_ai_service.moderate_content(text))

            return FilterResult(
                passed=result.passed,
                score=result.score,
                categories=result.categories,
                flagged_fragments=[],  # Mistral не возвращает фрагменты
                level3_score=result.score,
                llm_analysis=result.analysis,
            )
        except Exception as e:
            logger.error(f"Mistral LLM check failed: {e}")

        return FilterResult(passed=True, score=0.0)

    async def _llm_check_async(self, text: str, timeout: float = 3.0) -> FilterResult:
        """
        Уровень 3: LLM проверка через Mistral AI с таймаутом.
        Асинхронная версия для использования в async контексте.

        Args:
            text: Текст для проверки.
            timeout: Таймаут в секундах.

        Returns:
            FilterResult с результатами.

        Raises:
            asyncio.TimeoutError: При превышении таймаута.
        """
        from src.core.services.mistral_ai_service import mistral_ai_service

        try:
            # Выполняем асинхронный вызов с таймаутом
            result = await asyncio.wait_for(
                mistral_ai_service.moderate_content(text),
                timeout=timeout,
            )

            return FilterResult(
                passed=result.passed,
                score=result.score,
                categories=result.categories,
                flagged_fragments=[],  # Mistral не возвращает фрагменты
                level3_score=result.score,
                llm_analysis=result.analysis,
            )
        except TimeoutError:
            raise  # Пробрасываем таймаут выше
        except Exception as e:
            logger.error(f"Mistral LLM async check failed: {e}")
            raise  # Пробрасываем ошибку выше

    def _merge_categories(self, *category_lists: list[str]) -> list[str]:
        """Объединить списки категорий."""
        all_categories: set[str] = set()
        for categories in category_lists:
            all_categories.update(categories)
        return list(all_categories)

    def _merge_fragments(self, *fragment_lists: list[str]) -> list[str]:
        """Объединить списки фрагментов."""
        all_fragments: set[str] = set()
        for fragments in fragment_lists:
            all_fragments.update(fragments)
        return list(all_fragments)[:20]


# Глобальный экземпляр
_filter: ContentFilter | None = None


def get_filter() -> ContentFilter:
    """Получить глобальный экземпляр фильтра."""
    global _filter
    if _filter is None:
        _filter = ContentFilter()
    return _filter


async def check(text: str) -> FilterResult:
    """
    Проверить текст на запрещенный контент.

    Args:
        text: Текст для проверки.

    Returns:
        FilterResult с результатами.
    """
    return await get_filter().check(text)
