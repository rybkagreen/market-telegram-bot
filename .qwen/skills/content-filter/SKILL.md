---
name: content-filter
description: "MUST BE USED for content moderation: 3-level pipeline (regex → pymorphy3 → Mistral LLM), stop-word categories, policy enforcement, FilterResult validation. Use when checking advertising text, adding stop-word categories, testing moderation rules, or extending the moderation service. Enforces: ContentFilter singleton, check() before campaign creation, 10+ tests per new category."
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# Content Filter — 3-Level Pipeline

Трёхуровневая система модерации рекламного текста перед отправкой.
Защищает от запрещённого контента: наркотики, оружие, мошенничество, и др.

## When to Use
- Проверка рекламного текста перед созданием кампании
- Проверка текста перед отправкой в чаты
- Добавление новых категорий стоп-слов
- Написание unit-тестов для фильтра
- Расширение логики модерации
- Отладка ложных срабатываний

## Categories (stopwords_ru.json)

| Ключ | Описание |
|---|---|
| `drugs` | Наркотики и психотропные вещества |
| `terrorism` | Террористический контент |
| `weapons` | Оружие |
| `adult` | Контент для взрослых |
| `fraud` | Мошенничество |
| `suicide` | Суицидальный контент |
| `extremism` | Экстремизм |
| `gambling` | Азартные игры |

## Pipeline Levels

- **Level 1 — Regex:** быстрая проверка по паттернам, ~1ms
- **Level 2 — pymorphy3:** морфологический анализ (нормальная форма слов), ~10ms
- **Level 3 — LLM:** семантический анализ через Claude API (только при score > 0.5), ~500ms

## Instructions

1. Используй `ContentFilter` как синглтон через DI или `@lru_cache`
2. Вызывай `await cf.check(text)` перед созданием/запуском кампании
3. При `result.passed == False` — верни пользователю `result.flagged_fragments`
4. При добавлении категории — обязательно добавь 10+ тестов
5. Не изменяй порог `score` без тестирования на реальных примерах

## Usage

```python
from src.utils.content_filter.filter import ContentFilter
from src.config.settings import settings

cf = ContentFilter(settings)
result = await cf.check("your ad text here")

if not result.passed:
    # result.categories → ["drugs"]
    # result.flagged_fragments → ["закладка", "героин"]
    # result.score → 0.87
    await message.answer(
        f"❌ Текст не прошёл проверку.\n"
        f"Категории: {', '.join(result.categories)}\n"
        f"Фрагменты: {', '.join(result.flagged_fragments)}"
    )
```

## Adding a New Category

```python
# 1. Добавь в src/utils/content_filter/stopwords_ru.json
{
  "new_category": {
    "words": ["слово1", "слово2"],
    "patterns": ["паттерн\\d+"]
  }
}

# 2. Добавь в CategoryEnum
class Category(str, Enum):
    NEW_CATEGORY = "new_category"

# 3. Добавь 10+ тестов
# tests/unit/test_content_filter.py
@pytest.mark.parametrize("text,should_flag", [
    ("текст со словом1", True),
    ("безобидный текст", False),
])
@pytest.mark.asyncio
async def test_new_category(text: str, should_flag: bool, content_filter: ContentFilter) -> None:
    result = await content_filter.check(text)
    assert result.passed == (not should_flag)

# 4. Запусти тесты
# pytest tests/unit/test_content_filter.py -v
```

## FilterResult Schema

```python
from dataclasses import dataclass

@dataclass
class FilterResult:
    passed: bool                    # True если текст чистый
    score: float                    # 0.0–1.0, вероятность нарушения
    categories: list[str]           # список сработавших категорий
    flagged_fragments: list[str]    # конкретные слова/фразы
    level_reached: int              # 1, 2 или 3 — на каком уровне остановились
```
