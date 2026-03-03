# 📊 Расширение аналитики и тарифной сетки — Qwen Code промты

## Анализ проблем оригинального документа

| Проблема | Оригинал | Исправлено |
|---|---|---|
| Несуществующие данные | `fake_followers_percent`, `audience_geo_top3`, `audience_gender` — требуют платного TGStat API | Убраны. Оставлены только поля которые можно вычислить из данных парсера |
| Исторический рост | `subscribers_growth_7d/30d` требует хранения истории снимков | Реализован через отдельную `ChannelSnapshot` таблицу с периодической записью |
| Цены в рублях | `price_month: 990` — противоречит существующей кредитной системе в billing.py | Всё в кредитах, как уже реализовано |
| Планирование | 63 подкатегории сразу — несовместимо с существующим seed (6 топиков) | Расширение категорий как миграция поверх существующих данных |
| AI-аналитика | Описана абстрактно без связи с OpenRouter | Конкретный промпт через существующий `ai_service.py` |
| Временные рамки | 8-12 недель монолитно | 4 независимых Qwen Code промта, каждый 3-5 дней |
| Миграция | Ссылается на несуществующую `channel_analytics` таблицу | Правильные Alembic команды для существующей структуры |

---

## Структура: 4 независимых Qwen Code промта

```
Промт A (3 дня):  ChannelSnapshot + расширение категорий + тариф-фильтрация
Промт B (4 дня):  63 подкатегории в парсере + пересев данных
Промт C (3 дня):  AI-аналитика кампаний через OpenRouter (PRO/BUSINESS)
Промт D (3 дня):  Страница сравнения тарифов + предпросмотр каналов в Mini App
```

---

---

# ПРОМТ A: ChannelSnapshot + расширение категорий

## ⚠️ ПРАВИЛО — виртуальное окружение

```bash
source .venv/Scripts/activate   # Windows
source .venv/bin/activate        # Linux/Mac
```

## Шаг A.1 — Прочитать файлы

```
Read src/db/models/chat.py
Read src/db/models/user.py
Read src/db/base.py
Read src/db/session.py
Read src/config/settings.py
Read alembic/env.py
Read src/utils/telegram/parser.py
Read src/tasks/parser_tasks.py
```

---

## Шаг A.2 — Создать модель ChannelSnapshot

Создать `src/db/models/channel_snapshot.py`:

```python
"""
Исторические снимки метрик канала.

Парсер делает снимок 1 раз в 7 дней для каждого канала.
Это позволяет считать реальный прирост подписчиков.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base


class ChannelSnapshot(Base):
    __tablename__ = "channel_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK на основную таблицу каналов
    # Заменить chat_id на правильный FK после чтения chat.py
    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False
    )

    # Метрики на момент снимка
    member_count: Mapped[int | None] = mapped_column(Integer)
    avg_views: Mapped[float | None] = mapped_column(Float)   # Из последних 10 постов
    er_rate: Mapped[float | None] = mapped_column(Float)     # ER = avg_reactions/members*100
    posts_per_week: Mapped[float | None] = mapped_column(Float)

    # Временная метка снимка
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Поиск по каналу + дате
        Index("ix_snapshot_chat_date", "chat_id", "snapshot_date"),
        # Быстрый подсчёт прироста
        Index("ix_snapshot_date", "snapshot_date"),
    )
```

---

## Шаг A.3 — Alembic миграция

```bash
# Создать миграцию
alembic revision --autogenerate -m "add_channel_snapshots"

# Проверить сгенерированный файл
# alembic/versions/XXXX_add_channel_snapshots.py
# Убедиться что create_table правильный

# Применить
alembic upgrade head

# Проверить
docker compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} \
  -c "\d channel_snapshots"
```

---

## Шаг A.4 — Расширить константы категорий

Создать `src/utils/categories.py`:

```python
"""
Расширенные категории каналов.

Текущие данные в БД: 6 базовых топиков из seed скрипта.
Этот модуль добавляет подкатегории поверх существующих данных.

ВАЖНО: базовые категории (ключи верхнего уровня) должны совпадать
с реальными значениями поля topic/primary_category в таблице telegram_chats.
Проверить в парсере: src/utils/telegram/parser.py
"""

# Базовые категории → подкатегории
# Ключи должны совпадать с реальными значениями в БД
SUBCATEGORIES = {
    "бизнес": {
        "startup":          "Стартапы и инновации",
        "small_business":   "Малый бизнес и ИП",
        "franchise":        "Франчайзинг",
        "personal_finance": "Личные финансы",
    },
    "маркетинг": {
        "digital":    "Digital-маркетинг",
        "smm":        "SMM и соцсети",
        "target_ads": "Таргетированная реклама",
        "sales":      "Воронки продаж",
    },
    "it": {
        "programming": "Программирование",
        "web_dev":     "Веб-разработка",
        "mobile_dev":  "Мобильная разработка",
        "ai_ml":       "ИИ и машинное обучение",
        "data":        "Data Science",
        "devops":      "DevOps и облака",
        "security":    "Кибербезопасность",
        "gamedev":     "Разработка игр",
    },
    "финансы": {
        "investments":  "Инвестиции и трейдинг",
        "crypto":       "Криптовалюты",
        "stock_market": "Фондовый рынок",
        "real_estate":  "Инвестиции в недвижимость",
    },
    "крипто": {
        "defi":       "DeFi и протоколы",
        "nft":        "NFT и метавселенные",
        "blockchain": "Блокчейн-технологии",
        "trading":    "Крипто-трейдинг",
    },
    "образование": {
        "online_courses": "Онлайн-курсы",
        "languages":      "Изучение языков",
        "professional":   "Профессии и переквалификация",
        "kids":           "Детское образование",
    },
}

# Плоский список всех подкатегорий
ALL_SUBCATEGORIES = {
    subcat: name
    for subcats in SUBCATEGORIES.values()
    for subcat, name in subcats.items()
}

# Маппинг подкатегория → родительская категория
SUBCATEGORY_TO_PARENT = {
    subcat: parent
    for parent, subcats in SUBCATEGORIES.items()
    for subcat in subcats
}

# Ключевые слова для автоматического определения подкатегории
# Парсер использует это для автоклассификации при обходе каналов
SUBCATEGORY_KEYWORDS = {
    "startup":     ["стартап", "startup", "инновации", "mvp", "фаундер", "pivot"],
    "smm":         ["smm", "instagram", "тикток", "reels", "контент-маркетинг"],
    "ai_ml":       ["chatgpt", "llm", "нейросети", "machine learning", "openai", "claude"],
    "crypto":      ["bitcoin", "btc", "ethereum", "defi", "web3", "блокчейн"],
    "investments": ["акции", "облигации", "портфель", "дивиденды", "etf"],
    "devops":      ["docker", "kubernetes", "k8s", "ci/cd", "devops", "aws", "gcp"],
    "programming": ["python", "javascript", "golang", "rust", "leetcode", "код"],
    "gamedev":     ["unity", "unreal", "gamedev", "разработка игр", "геймдев"],
}
```

---

## Шаг A.5 — Добавить поле subcategory в модель чата

Прочитать `src/db/models/chat.py` и добавить поле:

```python
# В класс TelegramChat (или как называется модель) добавить:
subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
```

Создать миграцию:
```bash
alembic revision --autogenerate -m "add_subcategory_to_chats"
alembic upgrade head
```

---

## Шаг A.6 — Задача Celery для снимков

В `src/tasks/parser_tasks.py` добавить задачу:

```python
@celery_app.task(name="tasks.take_channel_snapshots")
def take_channel_snapshots() -> dict:
    """
    Делает снимок текущих метрик для всех активных каналов.
    Запускается раз в 7 дней.
    Данные используются для расчёта прироста подписчиков.
    """
    import asyncio
    return asyncio.run(_take_snapshots_async())


async def _take_snapshots_async() -> dict:
    from sqlalchemy import select
    from src.db.models.chat import TelegramChat  # реальное имя модели
    from src.db.models.channel_snapshot import ChannelSnapshot
    from src.db.session import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(
            select(TelegramChat.id, TelegramChat.member_count)
            .where(TelegramChat.is_active == True)
        )
        chats = result.all()

        count = 0
        for chat_id, member_count in chats:
            snapshot = ChannelSnapshot(
                chat_id=chat_id,
                member_count=member_count,
            )
            session.add(snapshot)
            count += 1

        await session.commit()

    return {"snapshots_created": count}
```

В расписание Celery Beat добавить:
```python
# В src/tasks/celery_config.py или где настраивается beat_schedule:
"take-channel-snapshots": {
    "task": "tasks.take_channel_snapshots",
    "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Каждый понедельник 03:00
},
```

---

## Шаг A.7 — Обновить константы тарифов

В `src/api/constants/tariffs.py` (создан в промте PUBLIC_CHANNEL_STATS_PLAN):

```python
# Добавить расчёт прироста через snapshots
SNAPSHOT_GROWTH_QUERY = """
SELECT 
    c.id,
    c.member_count as current,
    s_old.member_count as week_ago,
    (c.member_count - s_old.member_count) as growth_7d
FROM telegram_chats c
LEFT JOIN channel_snapshots s_old ON s_old.chat_id = c.id
    AND s_old.snapshot_date = (
        SELECT MAX(snapshot_date) 
        FROM channel_snapshots 
        WHERE chat_id = c.id 
        AND snapshot_date < NOW() - INTERVAL '6 days'
    )
WHERE c.is_active = true
"""
```

---

## Коммит A

```bash
git add \
  src/db/models/channel_snapshot.py \
  src/utils/categories.py \
  src/tasks/parser_tasks.py \
  alembic/versions/

git commit -m "feat(db): add ChannelSnapshot model and expanded categories

- ChannelSnapshot: weekly metric snapshots for growth calculation
  (member_count, avg_views, er_rate, posts_per_week)
- categories.py: 63 subcategories mapped from 6 existing base topics
- Celery task: take_channel_snapshots (weekly, Monday 03:00)
- Alembic migrations: channel_snapshots + subcategory column"

git push origin developer2/belin
```

---

---

# ПРОМТ B: Автоклассификация подкатегорий в парсере

## Шаг B.1 — Прочитать файлы

```
Read src/utils/telegram/parser.py
Read src/tasks/parser_tasks.py
Read src/utils/categories.py
Read src/db/models/chat.py
```

---

## Шаг B.2 — Добавить автоклассификацию в парсер

В `src/utils/telegram/parser.py` найти метод который обрабатывает/сохраняет канал и добавить:

```python
from src.utils.categories import SUBCATEGORY_KEYWORDS, SUBCATEGORY_TO_PARENT


def classify_subcategory(title: str, description: str, primary_topic: str) -> str | None:
    """
    Определить подкатегорию канала по ключевым словам в описании и названии.

    Args:
        title: Название канала
        description: Описание канала
        primary_topic: Уже определённая основная категория

    Returns:
        Код подкатегории или None если не удалось определить
    """
    if not title and not description:
        return None

    text = f"{title} {description}".lower()

    # Считаем совпадения для каждой подкатегории
    scores: dict[str, int] = {}
    for subcat, keywords in SUBCATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            # Проверяем что подкатегория относится к нужной родительской категории
            parent = SUBCATEGORY_TO_PARENT.get(subcat)
            if parent == primary_topic:
                scores[subcat] = score

    if not scores:
        return None

    # Возвращаем подкатегорию с наибольшим числом совпадений
    return max(scores, key=lambda k: scores[k])


# Вызвать classify_subcategory при сохранении/обновлении канала:
# channel.subcategory = classify_subcategory(
#     title=channel.title or "",
#     description=channel.description or "",
#     primary_topic=channel.primary_topic or "",
# )
```

---

## Шаг B.3 — Скрипт бэкфилла подкатегорий

Создать `scripts/backfill_subcategories.py`:

```python
"""
Заполнить поле subcategory для существующих каналов в БД.
Запускать один раз после применения миграции из Промта A.

Использование:
    cd c:\\Users\\alex_\\python-projects\\market-telegram-bot
    .venv\\Scripts\\python scripts/backfill_subcategories.py
"""
import asyncio
import sys
from pathlib import Path

# Добавить корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from src.db.models.chat import TelegramChat  # Заменить на реальное имя
from src.db.session import async_session_factory
from src.utils.categories import classify_subcategory


async def main():
    async with async_session_factory() as session:
        # Загружаем все каналы без подкатегории
        result = await session.execute(
            select(TelegramChat.id, TelegramChat.title, TelegramChat.description, TelegramChat.primary_topic)
            .where(
                TelegramChat.is_active == True,
                TelegramChat.subcategory.is_(None),
            )
        )
        chats = result.all()

        print(f"Обрабатываем {len(chats)} каналов...")

        updated = 0
        for chat_id, title, description, topic in chats:
            subcat = classify_subcategory(
                title=title or "",
                description=description or "",
                primary_topic=topic or "",
            )
            if subcat:
                await session.execute(
                    update(TelegramChat)
                    .where(TelegramChat.id == chat_id)
                    .values(subcategory=subcat)
                )
                updated += 1

        await session.commit()
        print(f"✅ Обновлено: {updated} из {len(chats)}")


if __name__ == "__main__":
    asyncio.run(main())
```

Запустить:
```bash
.venv/Scripts/python scripts/backfill_subcategories.py
# → ✅ Обновлено: N из 493
```

---

## Шаг B.4 — Расширить endpoint /api/channels/stats

В `src/api/routers/channels.py` добавить группировку по подкатегориям:

```python
@router.get("/subcategories/{parent_category}")
async def get_subcategory_stats(parent_category: str):
    """
    Детальная статистика по подкатегориям внутри категории.
    """
    from src.db.models.chat import TelegramChat as Chat
    from src.utils.categories import SUBCATEGORIES

    subcats = SUBCATEGORIES.get(parent_category, {})
    if not subcats:
        raise HTTPException(status_code=404, detail="Category not found")

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                Chat.subcategory.label("subcat"),
                func.count(Chat.id).label("total"),
                func.max(Chat.member_count).label("max_subscribers"),
                func.avg(Chat.member_count).label("avg_subscribers"),
            )
            .where(
                Chat.is_active == True,
                Chat.primary_topic == parent_category,
                Chat.subcategory.in_(list(subcats.keys())),
            )
            .group_by(Chat.subcategory)
        )
        rows = result.all()

    return {
        "category": parent_category,
        "subcategories": [
            {
                "code": row.subcat,
                "name": subcats.get(row.subcat, row.subcat),
                "total": row.total,
                "max_subscribers": row.max_subscribers or 0,
                "avg_subscribers": round(row.avg_subscribers or 0),
            }
            for row in rows
        ],
    }
```

---

## Коммит B

```bash
git add \
  src/utils/telegram/parser.py \
  scripts/backfill_subcategories.py \
  src/api/routers/channels.py

git commit -m "feat(parser): add subcategory auto-classification

- classify_subcategory(): keyword matching for 63 subcategories
- Parser now sets subcategory field on channel upsert
- backfill_subcategories.py: one-time script for existing 493 channels
- GET /api/channels/subcategories/{category}: detailed subcategory stats"

git push origin developer2/belin
```

---

---

# ПРОМТ C: AI-аналитика кампаний через OpenRouter

## Шаг C.1 — Прочитать файлы

```
Read src/core/services/ai_service.py
Read src/api/routers/analytics.py
Read src/api/dependencies.py
Read src/db/models/campaign.py
Read src/db/models/mailing_log.py
Read src/db/models/user.py
```

Нужно выяснить:
- Как устроен `ai_service.py` после миграции на OpenRouter
- Какой метод для генерации текста: `generate()`, `complete()`, `chat()`
- Формат ответа ai_service

---

## Шаг C.2 — Создать AI-аналитику кампаний

Создать `src/core/services/campaign_analytics_ai.py`:

```python
"""
AI-аналитика кампаний через OpenRouter.
Доступна только для тарифов PRO и BUSINESS.

Использует существующий ai_service.py.
"""
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class CampaignAnalyticsAI:
    """
    Генерирует AI-инсайты для завершённых кампаний.
    PRO: анализ + рекомендации
    BUSINESS: анализ + рекомендации + прогноз + сравнение с предыдущими
    """

    async def generate_campaign_insights(
        self,
        campaign_data: dict,
        plan: str,
    ) -> dict:
        """
        Сгенерировать AI-инсайты для кампании.

        Args:
            campaign_data: Данные кампании (title, sent, success_rate, topics, etc.)
            plan: Тариф пользователя ('pro' или 'business')

        Returns:
            dict с insights, recommendations, forecast (для business)
        """
        # Импортируем существующий ai_service
        # После чтения ai_service.py — использовать реальный метод
        from src.core.services.ai_service import AIService
        ai = AIService()

        prompt = self._build_prompt(campaign_data, plan)

        try:
            # Вызвать реальный метод ai_service — проверить сигнатуру после чтения
            response = await ai.generate(
                prompt=prompt,
                max_tokens=800,
                temperature=0.3,  # Низкая температура для аналитических текстов
            )
            return self._parse_response(response, plan)

        except Exception as e:
            logger.error(f"AI analytics error: {e}")
            return {
                "error": "Не удалось получить AI-анализ",
                "insights": [],
                "recommendations": [],
            }

    def _build_prompt(self, data: dict, plan: str) -> str:
        """Построить промпт для анализа кампании."""
        base = f"""Проанализируй результаты рекламной кампании в Telegram.

Данные кампании:
- Название: {data.get('title', 'Без названия')}
- Отправлено: {data.get('sent', 0)}
- Ошибок: {data.get('failed', 0)}
- Процент успеха: {data.get('success_rate', 0)}%
- Тематика: {', '.join(data.get('topics', [])) or 'не указана'}
- Дата: {data.get('date', datetime.now(UTC).strftime('%d.%m.%Y'))}

Средний успех по платформе: ~85-90%

Ответь в формате JSON:
{{
  "insights": ["Инсайт 1", "Инсайт 2", "Инсайт 3"],
  "recommendations": ["Рекомендация 1", "Рекомендация 2"],
  "performance_grade": "A/B/C/D"
}}"""

        if plan == "business":
            base += """

Дополнительно для BUSINESS тарифа:
- Сравни с предыдущими кампаниями если данные есть
- Добавь прогноз для следующей кампании
- Предложи A/B тест

Добавь в JSON поля:
  "forecast": "Прогноз для следующей кампании",
  "ab_test_suggestion": "Идея для A/B теста"
"""
        return base

    def _parse_response(self, response: str, plan: str) -> dict:
        """Парсить JSON-ответ от AI."""
        import json
        import re

        # Ищем JSON в ответе
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return {
                "insights": [response],
                "recommendations": [],
                "performance_grade": "N/A",
            }

        try:
            data = json.loads(json_match.group())
            return data
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI JSON response: {response[:200]}")
            return {
                "insights": ["Анализ получен, но не удалось его структурировать."],
                "recommendations": [],
                "performance_grade": "N/A",
            }


campaign_analytics_ai = CampaignAnalyticsAI()
```

---

## Шаг C.3 — Добавить endpoint в analytics роутер

В `src/api/routers/analytics.py` добавить:

```python
# ─── Схемы для AI-аналитики ─────────────────────────────────────

class AIInsightsResponse(BaseModel):
    campaign_id: int
    plan: str
    insights: list[str]
    recommendations: list[str]
    performance_grade: str
    forecast: str | None = None
    ab_test_suggestion: str | None = None
    generated_at: str


# ─── Endpoint ───────────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/ai-insights", response_model=AIInsightsResponse)
async def get_campaign_ai_insights(
    campaign_id: int,
    current_user: CurrentUser,
) -> AIInsightsResponse:
    """
    AI-аналитика конкретной кампании через OpenRouter.
    Доступна только для PRO и BUSINESS тарифов.
    Списывает 1 ИИ-генерацию из лимита пользователя.
    """
    from fastapi import HTTPException, status as http_status
    from sqlalchemy import update

    plan_str = _plan_label(current_user.plan)

    # Проверка тарифа
    if plan_str not in ("pro", "business"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="AI insights available for PRO and BUSINESS plans only",
        )

    # Проверка лимита генераций
    ai_limits = {"pro": 5, "business": 20}
    limit = ai_limits.get(plan_str, 0)
    if current_user.ai_generations_used >= limit and plan_str != "business":
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"AI generation limit reached ({current_user.ai_generations_used}/{limit})",
        )

    # Получаем данные кампании
    async with async_session_factory() as session:
        from src.db.models.campaign import Campaign
        from sqlalchemy import select
        result = await session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.user_id == current_user.id,
            )
        )
        campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    camp_status = (
        campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status)
    )
    if camp_status != "done":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="AI insights available only for completed campaigns",
        )

    # Получаем статистику
    stats_data = await get_campaign_stats(campaign_id, current_user)

    campaign_data = {
        "title": campaign.title or "Без названия",
        "sent": stats_data.sent,
        "failed": stats_data.failed,
        "success_rate": stats_data.success_rate,
        "topics": (campaign.filters_json or {}).get("topics", []),
        "date": stats_data.started_at or "",
    }

    # Вызываем AI
    from src.core.services.campaign_analytics_ai import campaign_analytics_ai
    result = await campaign_analytics_ai.generate_campaign_insights(
        campaign_data=campaign_data,
        plan=plan_str,
    )

    # Списываем генерацию
    async with async_session_factory() as session:
        from src.db.models.user import User
        from sqlalchemy import update
        await session.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(ai_generations_used=current_user.ai_generations_used + 1)
        )
        await session.commit()

    return AIInsightsResponse(
        campaign_id=campaign_id,
        plan=plan_str,
        insights=result.get("insights", []),
        recommendations=result.get("recommendations", []),
        performance_grade=result.get("performance_grade", "N/A"),
        forecast=result.get("forecast"),
        ab_test_suggestion=result.get("ab_test_suggestion"),
        generated_at=datetime.now(UTC).isoformat(),
    )
```

---

## Шаг C.4 — Добавить AI инсайты в CampaignDetail (Mini App)

В `mini_app/src/api/analytics.ts` добавить:

```typescript
export interface AIInsights {
  campaign_id: number
  plan: string
  insights: string[]
  recommendations: string[]
  performance_grade: 'A' | 'B' | 'C' | 'D' | 'N/A'
  forecast: string | null
  ab_test_suggestion: string | null
  generated_at: string
}

// В analyticsApi добавить:
campaignAiInsights: (campaignId: number): Promise<AIInsights> =>
  apiClient.get(`/analytics/campaigns/${campaignId}/ai-insights`).then(r => r.data),
```

В `mini_app/src/components/CampaignDetail.tsx` добавить кнопку AI-аналитики:

```tsx
// В компонент CampaignDetail добавить:
const user = useAuthStore(s => s.user)
const isPaidPlan = ['pro', 'business'].includes(user?.plan ?? '')

const aiMutation = useMutation({
  mutationFn: () => analyticsApi.campaignAiInsights(campaign!.id),
  onSuccess: () => {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
  },
})

// В JSX добавить кнопку и блок инсайтов:
{isPaidPlan && campaign?.status === 'done' && (
  <div style={{ marginTop: 16 }}>
    {!aiMutation.data ? (
      <button
        className="btn btn-ghost"
        onClick={() => aiMutation.mutate()}
        disabled={aiMutation.isPending}
        style={{ width: '100%' }}
      >
        {aiMutation.isPending ? '🤖 Анализирую...' : '🤖 AI-анализ кампании'}
      </button>
    ) : (
      <div style={{
        background: 'rgba(99,102,241,0.08)',
        border: '1px solid var(--border-accent)',
        borderRadius: 12, padding: 14,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <p style={{ fontSize: 13, fontWeight: 700 }}>🤖 AI-анализ</p>
          <span style={{
            fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-display)',
            color: {A: 'var(--success)', B: 'var(--info)', C: 'var(--warning)', D: 'var(--danger)'}[aiMutation.data.performance_grade] ?? 'var(--text-muted)',
          }}>
            {aiMutation.data.performance_grade}
          </span>
        </div>
        {aiMutation.data.insights.map((insight, i) => (
          <p key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
            💡 {insight}
          </p>
        ))}
        {aiMutation.data.recommendations.map((rec, i) => (
          <p key={i} style={{ fontSize: 12, color: 'var(--success)', marginBottom: 6 }}>
            ✅ {rec}
          </p>
        ))}
        {aiMutation.data.forecast && (
          <p style={{ fontSize: 12, color: 'var(--accent-400)', marginTop: 8 }}>
            📈 {aiMutation.data.forecast}
          </p>
        )}
      </div>
    )}
  </div>
)}
```

---

## Коммит C

```bash
git add \
  src/core/services/campaign_analytics_ai.py \
  src/api/routers/analytics.py \
  mini_app/src/api/analytics.ts \
  mini_app/src/components/CampaignDetail.tsx

git commit -m "feat(ai): add AI campaign insights via OpenRouter

Backend:
  - CampaignAnalyticsAI: generates insights, recommendations, grade
  - GET /api/analytics/campaigns/{id}/ai-insights (PRO/BUSINESS only)
  - Deducts 1 AI generation from user limit
  - Business plan gets forecast + A/B test suggestion

Frontend:
  - CampaignDetail: '🤖 AI-анализ' button (hidden for FREE/STARTER)
  - Shows insights, recommendations, performance grade (A/B/C/D)
  - Business plan: forecast and A/B suggestion visible"

git push origin developer2/belin
```

---

---

# ПРОМТ D: Страница сравнения тарифов в Mini App

## Шаг D.1 — Прочитать файлы

```
Read mini_app/src/pages/Billing.tsx
Read mini_app/src/styles/tokens.css
Read mini_app/src/api/channels.ts
Read mini_app/src/store/authStore.ts
```

---

## Шаг D.2 — Создать страницу Plans (отдельно от Billing)

Создать `mini_app/src/pages/Plans.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { channelsApi } from '@/api/channels'
import { useAuthStore } from '@/store/authStore'

// Фичи каждого тарифа
const PLAN_FEATURES: Record<string, {
  emoji: string
  name: string
  color: string
  price_credits: number
  channels_access: string
  campaigns: string
  ai_gen: string
  ai_analytics: boolean
  features: string[]
}> = {
  free: {
    emoji: '🆓', name: 'FREE', color: 'var(--neutral)',
    price_credits: 0,
    channels_access: 'до 10K подписчиков',
    campaigns: '1 в месяц',
    ai_gen: 'недоступно',
    ai_analytics: false,
    features: ['2 категории каналов', 'Базовая аналитика'],
  },
  starter: {
    emoji: '🚀', name: 'STARTER', color: 'var(--info)',
    price_credits: 299,
    channels_access: 'до 50K подписчиков',
    campaigns: '5 в месяц',
    ai_gen: '5 генераций/мес',
    ai_analytics: false,
    features: ['5 категорий каналов', 'Расширенная аналитика', '🦙 Llama 4 Scout'],
  },
  pro: {
    emoji: '💎', name: 'PRO', color: 'var(--accent-400)',
    price_credits: 999,
    channels_access: 'до 200K подписчиков',
    campaigns: '20 в месяц',
    ai_gen: '5 генераций/мес',
    ai_analytics: true,
    features: [
      'Все категории (без Premium)',
      'Расширенная аналитика',
      '✨ Claude Sonnet 4.6',
      'AI-анализ кампаний',
      'Топ чатов разблокирован',
    ],
  },
  business: {
    emoji: '🏢', name: 'BUSINESS', color: 'var(--warning)',
    price_credits: 2999,
    channels_access: 'Все + 💎 Premium (>1M)',
    campaigns: 'Безлимит',
    ai_gen: '20 генераций/мес',
    ai_analytics: true,
    features: [
      'ВСЕ категории включая Premium',
      '✨ Claude Sonnet 4.6',
      'AI-анализ + прогноз + A/B',
      'Анализ конкурентов',
      'Полная аналитика',
    ],
  },
}

export default function Plans() {
  const user = useAuthStore(s => s.user)
  const navigate = useNavigate()
  const currentPlan = user?.plan ?? 'free'

  const { data: channelStats } = useQuery({
    queryKey: ['channels', 'stats'],
    queryFn: channelsApi.stats,
    staleTime: 10 * 60_000,
  })

  return (
    <div className="page-content page-enter">
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Тарифы</h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Выберите план для вашего бизнеса
        </p>
      </div>

      {Object.entries(PLAN_FEATURES).map(([planKey, info], i) => {
        const isActive = planKey === currentPlan
        const channelCount = channelStats?.tariff_stats.find(s => s.tariff === planKey)?.available

        return (
          <motion.div
            key={planKey}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            style={{
              background: isActive
                ? `linear-gradient(135deg, ${info.color}15, var(--bg-surface))`
                : 'var(--bg-surface)',
              border: `2px solid ${isActive ? info.color : 'var(--border)'}`,
              borderRadius: 18,
              padding: '18px 16px',
              marginBottom: 12,
            }}
          >
            {/* Шапка */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 24 }}>{info.emoji}</span>
                <div>
                  <p style={{ fontSize: 16, fontWeight: 700 }}>{info.name}</p>
                  {isActive && (
                    <p style={{ fontSize: 11, color: info.color, fontWeight: 600 }}>АКТИВЕН</p>
                  )}
                </div>
              </div>
              <p className="font-mono" style={{ fontSize: 16, fontWeight: 700, color: info.color }}>
                {info.price_credits === 0 ? 'Бесплатно' : `${info.price_credits} кр/мес`}
              </p>
            </div>

            {/* Ключевые метрики */}
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr 1fr',
              gap: 8, marginBottom: 12,
            }}>
              {[
                { label: '📡 Каналов', value: channelCount ? channelCount.toLocaleString('ru') : '...' },
                { label: '📊 Кампании', value: info.campaigns },
                { label: '🤖 ИИ', value: info.ai_gen },
                { label: '📈 AI-аналитика', value: info.ai_analytics ? '✅ Да' : '❌ Нет' },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  background: 'var(--bg-elevated)',
                  borderRadius: 10, padding: '8px 10px',
                }}>
                  <p style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>{label}</p>
                  <p style={{ fontSize: 13, fontWeight: 600 }}>{value}</p>
                </div>
              ))}
            </div>

            {/* Лимит каналов */}
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
              Аудитория: {info.channels_access}
            </p>

            {/* Список фич */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
              {info.features.map(f => (
                <span key={f} style={{
                  fontSize: 11, padding: '3px 8px', borderRadius: 6,
                  background: 'var(--bg-elevated)',
                  color: 'var(--text-muted)',
                }}>
                  {f}
                </span>
              ))}
            </div>

            {/* Кнопка */}
            {!isActive ? (
              <button
                className="btn"
                onClick={() => navigate('/billing')}
                style={{
                  background: info.color + '22',
                  color: info.color,
                  border: `1px solid ${info.color + '44'}`,
                  fontSize: 14,
                }}
              >
                Перейти на {info.name}
              </button>
            ) : (
              <div style={{
                textAlign: 'center', padding: '10px 0',
                color: info.color, fontSize: 13, fontWeight: 600,
              }}>
                ✓ Ваш текущий тариф
              </div>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}
```

---

## Шаг D.3 — Добавить ссылку на Plans из Billing

В `mini_app/src/pages/Billing.tsx` в секцию "ТАРИФНЫЕ ПЛАНЫ" добавить кнопку:

```tsx
// В начале секции "ТАРИФНЫЕ ПЛАНЫ" добавить:
<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
  <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)' }}>
    ТАРИФНЫЕ ПЛАНЫ
  </p>
  <Link
    to="/plans"
    style={{ fontSize: 12, color: 'var(--accent-400)', textDecoration: 'none' }}
  >
    Сравнить →
  </Link>
</div>
```

---

## Шаг D.4 — Добавить маршрут /plans в App.tsx

```tsx
import Plans from '@/pages/Plans'
// В Routes:
<Route path="/plans" element={<Plans />} />
```

---

## Коммит D

```bash
cd mini_app
git add \
  src/pages/Plans.tsx \
  src/pages/Billing.tsx \
  src/App.tsx

git commit -m "feat(mini-app): add Plans comparison page

- Plans page: full tariff comparison with real channel counts
- Grid: channels accessible, campaigns, AI gen, AI analytics
- Shows real channel counts from /api/channels/stats
- Features as tags, active plan highlighted
- 'Сравнить →' link from Billing page"

git push origin developer2/belin
```

---

---

## Итоговый порядок реализации

```
Неделя 1: Промт PUBLIC_CHANNEL_STATS (отдельный файл) — страница "База"
Неделя 2: Промт A — ChannelSnapshot + подкатегории в БД
Неделя 3: Промт B — автоклассификация в парсере + бэкфилл
Неделя 4: Промт C — AI-аналитика кампаний
Неделя 5: Промт D — страница сравнения тарифов

После каждого промта:
  npm run build       # TypeScript без ошибок
  alembic upgrade head # Миграции применены
  docker compose restart api bot
```

## Что НЕ делаем (убрано из оригинала)

- ❌ `fake_followers_percent` — требует TGStat/Telemetr API (платно, ~$500/мес)
- ❌ `audience_geo_top3`, `audience_gender` — закрытые данные Telegram
- ❌ `estimated_post_price` — нет источника данных в проекте
- ❌ Цены в рублях — проект использует кредиты, не валюту напрямую
- ❌ White label, персональный менеджер — операционные процессы, не код
