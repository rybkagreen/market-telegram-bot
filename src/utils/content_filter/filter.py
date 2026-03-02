"""
Content Filter — 3-уровневая система проверки контента.

Уровни:
1. regex_check — быстрая проверка по стоп-словам (< 1 мс)
2. morph_check — проверка нормализованных словоформ (pymorphy3)
3. llm_check — LLM анализ через OpenRouter (бесплатная модель)

8 заблокированных категорий:
- drugs, terrorism, weapons, adult
- fraud, suicide, extremism, gambling
"""

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
LEVEL1_THRESHOLD = 0.1  # Если score > 0.1, переходим на уровень 2
LEVEL2_THRESHOLD = 0.3  # Если score > 0.3, переходим на уровень 3
LEVEL3_THRESHOLD = 0.5  # Если LLM score > 0.5, контент блокируется


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
            logger.info(f"Loaded {len(self._stopwords)} categories from {path}")
        except Exception as e:
            logger.error(f"Error loading stopwords: {e}")
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

    def check(self, text: str) -> FilterResult:
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
            return FilterResult(
                passed=combined_score < LEVEL3_THRESHOLD,
                score=combined_score,
                categories=level2_result.categories,
                flagged_fragments=level2_result.flagged_fragments,
                level1_score=level1_result.score,
                level2_score=level2_result.score,
            )

        # Уровень 3: LLM проверка
        level3_result = self._llm_check(text)
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
                level3_result.flagged_fragments,
            ),
            level1_score=level1_result.score,
            level2_score=level2_result.score,
            level3_score=level3_result.score,
            llm_analysis=level3_result.llm_analysis,
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

        categories: list[str] = []
        flagged: list[str] = []

        # Токенизируем текст
        words = re.findall(r"\w+", text.lower())

        # Нормализуем каждое слово
        normalized_words = []
        for word in words:
            try:
                parsed = self._morph.parse(word)[0]
                normalized = parsed.normal_form
                normalized_words.append(normalized)
            except Exception:
                normalized_words.append(word)

        # Проверяем нормализованные слова против стоп-слов
        for category, stopwords in self._stopwords.items():
            category_matches = []

            for i, norm_word in enumerate(normalized_words):
                for stopword in stopwords:
                    # Проверяем точное совпадение или частичное
                    if norm_word == stopword or (len(stopword) > 3 and stopword in norm_word):
                        category_matches.append(words[i])
                        break

            if category_matches:
                categories.append(category)
                flagged.extend(category_matches[:3])

        # Вычисляем score
        score = min(1.0, len(categories) * 0.2 + len(flagged) * 0.05)

        return FilterResult(
            passed=score < LEVEL3_THRESHOLD,
            score=score,
            categories=list(set(categories)),
            flagged_fragments=list(set(flagged))[:10],
        )

    def _llm_check(self, text: str) -> FilterResult:
        """
        Уровень 3: LLM проверка через OpenRouter API.

        Args:
            text: Текст для проверки.

        Returns:
            FilterResult с результатами.
        """
        from src.config.settings import settings

        # Проверяем наличие API ключа OpenRouter
        if not settings.openrouter_api_key:
            logger.warning("OpenRouter API key not configured, skipping LLM check")
            return FilterResult(passed=True, score=0.0)

        try:
            return self._call_openrouter(text, settings.openrouter_api_key, settings.model_free)
        except Exception as e:
            logger.error(f"LLM check failed: {e}")

        return FilterResult(passed=True, score=0.0)

    def _call_openrouter(self, text: str, api_key: str, model: str) -> FilterResult:
        """
        Вызвать OpenRouter API для анализа контента.

        Args:
            text: Текст для проверки.
            api_key: OpenRouter API ключ.
            model: Модель для анализа (из settings.model_free).

        Returns:
            FilterResult с результатами.
        """
        try:
            from openai import AsyncOpenAI

            # OpenRouter совместим с OpenAI API
            client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/rybkagreen/market-telegram-bot",
                    "X-OpenRouter-Title": "Market Telegram Bot",
                },
            )

            system_prompt = """Ты модератор контента для Telegram бота.
Твоя задача — определить, содержит ли текст запрещенный контент по законодательству РФ.

Категории для проверки:
- drugs: наркотики, продажа, употребление
- terrorism: терроризм, призывы к насилию
- weapons: оружие, продажа оружия
- adult: порнография, эротика 18+
- fraud: мошенничество, обман, пирамиды
- suicide: суицид, призывы к самоубийству
- extremism: экстремизм, нацизм, разжигание розни
- gambling: азартные игры, казино, ставки

Верни ответ в формате JSON:
{
    "passed": true/false,
    "score": 0.0-1.0,
    "categories": ["category1", "category2"],
    "analysis": "краткий анализ"
}

Если текст чистый — passed: true, score: 0.0
Если текст содержит нарушения — passed: false, score: 0.5-1.0"""

            user_prompt = f"Проверь этот текст на запрещенный контент:\n\n{text[:3000]}"

            import asyncio

            response = asyncio.get_event_loop().run_until_complete(
                client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=500,
                    response_format={"type": "json_object"},
                )
            )

            import json

            content = response.choices[0].message.content
            if content is None:
                return FilterResult(passed=True, score=0.0)

            result = json.loads(content)

            return FilterResult(
                passed=result.get("passed", True),
                score=float(result.get("score", 0.0)),
                categories=result.get("categories", []),
                llm_analysis=result.get("analysis", ""),
            )

        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return FilterResult(passed=True, score=0.0)

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


def check(text: str) -> FilterResult:
    """
    Проверить текст на запрещенный контент.

    Args:
        text: Текст для проверки.

    Returns:
        FilterResult с результатами.
    """
    return get_filter().check(text)
