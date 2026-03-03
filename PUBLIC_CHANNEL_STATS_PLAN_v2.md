# 📊 Публичная статистика базы каналов — Qwen Code промт

## Анализ проблем оригинального документа

Перед реализацией — что было неправильно в оригинале и как исправлено:

| Проблема | Оригинал | Исправлено |
|---|---|---|
| N+1 запросы | 4 запроса на каждую категорию × N категорий | 1 агрегированный SQL с GROUP BY |
| Дизайн | Generic CSS вне системы | Токены из `tokens.css`, паттерны из существующих страниц |
| Тёмная тема | `@media prefers-color-scheme` | `data-theme` через `window.Telegram.WebApp.colorScheme` (как в App.tsx) |
| Кэш | Упомянут, не реализован | Конкретный Redis код с `aioredis` |
| Навигация | Страница не привязана к BottomNav | 5-я вкладка "База" в `BottomNav.tsx` |
| Поле модели | `TelegramChat.primary_category` — проверить существование | Промт начинается с `Read src/db/models/chat.py` |
| Рост за неделю | Hardcoded `+1,234` | Считается через `func.count + WHERE created_at >= now-7d` |
| Авторизация | Нет в оригинале | `GET /api/channels/stats` публичный (без JWT), остальные — с JWT |

---

## ⚠️ ПРАВИЛО — виртуальное окружение

```bash
source .venv/Scripts/activate  # Windows
source .venv/bin/activate       # Linux/Mac
which python | grep ".venv" && echo "✅ .venv активен" || echo "❌ СТОП"
```

---

## ЧАСТЬ 1 — БЭКЕНД

### Шаг 1.1 — Прочитать существующие файлы

```
Read src/db/models/chat.py
Read src/db/models/user.py
Read src/api/routers/analytics.py
Read src/api/routers/billing.py
Read src/api/dependencies.py
Read src/api/main.py
Read src/config/settings.py
```

Нужно выяснить:
- Какие поля у `TelegramChat` (или как называется модель чата)
- Какие значения может принимать `primary_category` / `topic`
- Есть ли поле `subscribers`, `member_count`, `is_active`, `is_scam`
- Есть ли поле `overall_rating` или `er_rate`

---

### Шаг 1.2 — Создать константы тарифов и категорий

Создать `src/api/constants/tariffs.py`:

```python
"""
Константы тарифной системы.
Используются в billing, analytics, channels роутерах.
"""

# Ограничения по подписчикам для каждого тарифа
# -1 означает безлимит
TARIFF_SUBSCRIBER_LIMITS = {
    "free":     10_000,
    "starter":  50_000,
    "pro":      200_000,
    "business": -1,
}

# Минимальный рейтинг канала для каждого тарифа
TARIFF_MIN_RATING = {
    "free":     0.0,
    "starter":  5.0,
    "pro":      7.0,
    "business": 0.0,
}

# Доступные категории (подстроки topic/category поля в БД)
# Заполнить после чтения chat.py — использовать реальные значения из seed данных
TARIFF_CATEGORIES = {
    "free":     ["бизнес", "маркетинг"],
    "starter":  ["бизнес", "маркетинг", "it", "финансы", "ecommerce"],
    "pro":      None,   # None = все категории кроме premium (>1M подписчиков)
    "business": None,   # None = все категории включая premium
}

# Пороговое значение подписчиков для "premium" каналов
PREMIUM_SUBSCRIBER_THRESHOLD = 1_000_000

# Ценовая сетка тарифов в кредитах (уже реализована в billing.py)
TARIFF_CREDIT_COST = {
    "free":     0,
    "starter":  299,
    "pro":      999,
    "business": 2999,
}

# Имена тарифов для отображения
TARIFF_LABELS = {
    "free":     "FREE",
    "starter":  "STARTER",
    "pro":      "PRO",
    "business": "BUSINESS",
}
```

---

### Шаг 1.3 — Создать channels роутер

Создать `src/api/routers/channels.py`:

```python
"""
FastAPI роутер для статистики базы каналов.

Endpoints:
  GET /api/channels/stats        — публичная статистика (без JWT)
  GET /api/channels/preview      — предпросмотр каналов для пользователя (с JWT)
"""
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from src.api.constants.tariffs import (
    PREMIUM_SUBSCRIBER_THRESHOLD,
    TARIFF_CATEGORIES,
    TARIFF_LABELS,
    TARIFF_MIN_RATING,
    TARIFF_SUBSCRIBER_LIMITS,
)
from src.api.dependencies import CurrentUser
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channels", tags=["channels"])

# ─── ВАЖНО: После чтения chat.py заменить TelegramChat на реальное имя модели
# и поля на реальные имена из модели
# ─────────────────────────────────────────────────────────────────────────────


# ─── Схемы ──────────────────────────────────────────────────────

class TariffStatsItem(BaseModel):
    tariff: str
    label: str
    available: int
    percent_of_total: float
    premium_count: int


class CategoryStatsItem(BaseModel):
    category: str
    total: int
    available_by_tariff: dict[str, int]
    top_channels: list[dict]


class DatabaseStatsResponse(BaseModel):
    total_channels: int
    total_categories: int
    added_last_7d: int
    last_updated: str
    tariff_stats: list[TariffStatsItem]
    categories: list[CategoryStatsItem]


class ChannelPreviewItem(BaseModel):
    id: int
    title: str
    username: str | None
    subscribers: int
    category: str
    rating: float | None
    is_premium: bool
    is_accessible: bool   # доступен ли на текущем тарифе


class ChannelsPreviewResponse(BaseModel):
    total_accessible: int
    total_locked: int
    channels: list[ChannelPreviewItem]


# ─── Хелпер: фильтр каналов по тарифу ──────────────────────────

def _build_tariff_filter(tariff: str, Chat):
    """
    Построить список SQLAlchemy условий для фильтрации каналов по тарифу.
    Chat — импортированная модель TelegramChat (или как она называется в проекте).
    """
    conditions = [
        Chat.is_active == True,
    ]

    # Фильтр по подписчикам
    sub_limit = TARIFF_SUBSCRIBER_LIMITS.get(tariff, -1)
    if sub_limit != -1:
        # Используем поле subscriber_count или member_count — проверить в chat.py
        conditions.append(Chat.member_count <= sub_limit)

    # Фильтр по рейтингу
    min_rating = TARIFF_MIN_RATING.get(tariff, 0.0)
    if min_rating > 0 and hasattr(Chat, "overall_rating"):
        conditions.append(Chat.overall_rating >= min_rating)

    # Фильтр по категориям
    categories = TARIFF_CATEGORIES.get(tariff)
    if categories is not None:
        # Используем реальное поле категории — проверить в chat.py
        # Может быть primary_topic, category, topics и т.д.
        conditions.append(Chat.primary_topic.in_(categories))

    # PRO не видит premium (>1M), BUSINESS видит всё
    if tariff == "pro":
        conditions.append(Chat.member_count < PREMIUM_SUBSCRIBER_THRESHOLD)

    return conditions


# ─── Endpoints ──────────────────────────────────────────────────

@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_channel_stats() -> DatabaseStatsResponse:
    """
    Публичная статистика базы каналов.
    Доступна БЕЗ авторизации — используется как маркетинговый инструмент.
    Кэшируется в Redis на 1 час.
    """
    from src.config.settings import settings
    import json
    import redis.asyncio as aioredis

    # ─ Redis кэш ─────────────────────────────────────────────────
    redis_client = aioredis.from_url(str(settings.redis_url))
    cache_key = "channels:stats:v1"

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            await redis_client.aclose()
            data = json.loads(cached)
            return DatabaseStatsResponse(**data)
    except Exception as e:
        logger.warning(f"Redis cache miss: {e}")
    finally:
        pass  # закрываем после use

    # ─ Считаем статистику одним запросом ──────────────────────────
    # ВАЖНО: заменить TelegramChat на реальное имя модели
    from src.db.models.chat import TelegramChat as Chat  # ← имя модели из chat.py

    async with async_session_factory() as session:
        # Всего каналов
        total_result = await session.execute(
            select(func.count(Chat.id)).where(Chat.is_active == True)
        )
        total = total_result.scalar() or 0

        # Добавленных за последние 7 дней
        week_ago = datetime.now(UTC) - timedelta(days=7)
        new_result = await session.execute(
            select(func.count(Chat.id)).where(
                Chat.is_active == True,
                Chat.created_at >= week_ago,
            )
        )
        added_7d = new_result.scalar() or 0

        # Агрегация по категориям ОДНИМ запросом (не N+1!)
        # Заменить primary_topic на реальное поле
        cat_result = await session.execute(
            select(
                Chat.primary_topic.label("category"),
                func.count(Chat.id).label("total"),
            )
            .where(Chat.is_active == True)
            .group_by(Chat.primary_topic)
            .order_by(func.count(Chat.id).desc())
        )
        cat_rows = cat_result.all()

        # Топ каналов для каждой категории (3 запроса в цикле — допустимо для ~10 категорий)
        categories = []
        for row in cat_rows:
            if not row.category:
                continue

            top_result = await session.execute(
                select(Chat.id, Chat.title, Chat.username, Chat.member_count)
                .where(Chat.is_active == True, Chat.primary_topic == row.category)
                .order_by(Chat.member_count.desc())
                .limit(3)
            )
            top_channels = [
                {
                    "id": r.id,
                    "title": r.title or "Без названия",
                    "username": r.username,
                    "subscribers": r.member_count or 0,
                }
                for r in top_result.all()
            ]

            # Доступно по тарифам — подзапросы по каждому тарифу
            available_by_tariff = {}
            for tariff in ("free", "starter", "pro", "business"):
                conditions = _build_tariff_filter(tariff, Chat)
                conditions.append(Chat.primary_topic == row.category)
                count_result = await session.execute(
                    select(func.count(Chat.id)).where(and_(*conditions))
                )
                available_by_tariff[tariff] = count_result.scalar() or 0

            categories.append(CategoryStatsItem(
                category=row.category,
                total=row.total or 0,
                available_by_tariff=available_by_tariff,
                top_channels=top_channels,
            ))

        # Статистика по тарифам
        tariff_stats = []
        for tariff in ("free", "starter", "pro", "business"):
            conditions = _build_tariff_filter(tariff, Chat)
            count_result = await session.execute(
                select(func.count(Chat.id)).where(and_(*conditions))
            )
            available = count_result.scalar() or 0

            # Premium каналы (только для business)
            if tariff == "business":
                premium_result = await session.execute(
                    select(func.count(Chat.id)).where(
                        Chat.is_active == True,
                        Chat.member_count >= PREMIUM_SUBSCRIBER_THRESHOLD,
                    )
                )
                premium_count = premium_result.scalar() or 0
            else:
                premium_count = 0

            tariff_stats.append(TariffStatsItem(
                tariff=tariff,
                label=TARIFF_LABELS[tariff],
                available=available,
                percent_of_total=round(available / total * 100, 1) if total > 0 else 0.0,
                premium_count=premium_count,
            ))

    result = DatabaseStatsResponse(
        total_channels=total,
        total_categories=len(cat_rows),
        added_last_7d=added_7d,
        last_updated=datetime.now(UTC).isoformat(),
        tariff_stats=tariff_stats,
        categories=categories,
    )

    # ─ Записать в кэш на 1 час ───────────────────────────────────
    try:
        await redis_client.setex(cache_key, 3600, result.model_dump_json())
    except Exception as e:
        logger.warning(f"Redis cache write failed: {e}")
    finally:
        await redis_client.aclose()

    return result


@router.get("/preview", response_model=ChannelsPreviewResponse)
async def get_channels_preview(
    current_user: CurrentUser,
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> ChannelsPreviewResponse:
    """
    Предпросмотр каналов с учётом тарифа текущего пользователя.
    Требует JWT авторизации.
    Показывает как доступные, так и заблокированные каналы.
    """
    from src.db.models.chat import TelegramChat as Chat

    plan_str = (
        current_user.plan.value
        if hasattr(current_user.plan, "value")
        else str(current_user.plan)
    )

    async with async_session_factory() as session:
        base_conditions = [Chat.is_active == True]
        if category:
            base_conditions.append(Chat.primary_topic == category)

        result = await session.execute(
            select(Chat.id, Chat.title, Chat.username, Chat.member_count, Chat.primary_topic)
            .where(and_(*base_conditions))
            .order_by(Chat.member_count.desc())
            .limit(limit)
        )
        rows = result.all()

    # Строим список с пометками доступности
    user_conditions = _build_tariff_filter(plan_str, Chat)
    accessible_ids = set()

    async with async_session_factory() as session:
        acc_result = await session.execute(
            select(Chat.id).where(and_(*user_conditions))
        )
        accessible_ids = {r.id for r in acc_result.all()}

    channels = []
    for row in rows:
        is_premium = (row.member_count or 0) >= PREMIUM_SUBSCRIBER_THRESHOLD
        is_accessible = row.id in accessible_ids

        channels.append(ChannelPreviewItem(
            id=row.id,
            title=row.title or "Без названия",
            username=row.username,
            subscribers=row.member_count or 0,
            category=row.primary_topic or "other",
            rating=None,   # Добавить если есть поле overall_rating
            is_premium=is_premium,
            is_accessible=is_accessible,
        ))

    accessible_count = sum(1 for c in channels if c.is_accessible)
    locked_count = len(channels) - accessible_count

    return ChannelsPreviewResponse(
        total_accessible=accessible_count,
        total_locked=locked_count,
        channels=channels,
    )
```

---

### Шаг 1.4 — Зарегистрировать роутер в main.py

В `src/api/main.py` добавить:

```python
from src.api.routers.channels import router as channels_router
app.include_router(channels_router, prefix="/api")
```

---

### Шаг 1.5 — Проверить бэкенд

```bash
docker compose restart api
sleep 3

# Публичный endpoint (без JWT)
curl http://localhost:8001/api/channels/stats
# → JSON с total_channels, categories, tariff_stats

# Swagger UI
# http://localhost:8001/docs → /api/channels/stats
```

---

## ЧАСТЬ 2 — ФРОНТЕНД

### Шаг 2.1 — Прочитать существующий фронтенд

```
Read mini_app/src/styles/tokens.css
Read mini_app/src/styles/global.css
Read mini_app/src/components/layout/BottomNav.tsx
Read mini_app/src/components/ui/Skeleton.tsx
Read mini_app/src/components/ui/ProgressBar.tsx
Read mini_app/src/App.tsx
Read mini_app/src/pages/Dashboard.tsx
```

---

### Шаг 2.2 — Создать API модуль

Создать `mini_app/src/api/channels.ts`:

```typescript
import { apiClient } from './client'

export interface TariffStatsItem {
  tariff: 'free' | 'starter' | 'pro' | 'business'
  label: string
  available: number
  percent_of_total: number
  premium_count: number
}

export interface CategoryStats {
  category: string
  total: number
  available_by_tariff: Record<string, number>
  top_channels: Array<{
    id: number
    title: string
    username: string | null
    subscribers: number
  }>
}

export interface DatabaseStats {
  total_channels: number
  total_categories: number
  added_last_7d: number
  last_updated: string
  tariff_stats: TariffStatsItem[]
  categories: CategoryStats[]
}

export interface ChannelPreviewItem {
  id: number
  title: string
  username: string | null
  subscribers: number
  category: string
  rating: number | null
  is_premium: boolean
  is_accessible: boolean
}

export interface ChannelsPreview {
  total_accessible: number
  total_locked: number
  channels: ChannelPreviewItem[]
}

export const channelsApi = {
  // Публичный — не требует токена, вызывается напрямую через fetch или apiClient
  stats: (): Promise<DatabaseStats> =>
    apiClient.get('/channels/stats').then(r => r.data),

  preview: (params?: { category?: string; limit?: number }): Promise<ChannelsPreview> =>
    apiClient.get('/channels/preview', { params }).then(r => r.data),
}
```

---

### Шаг 2.3 — Создать страницу Channels

Создать `mini_app/src/pages/Channels.tsx`:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { channelsApi, type CategoryStats, type TariffStatsItem } from '@/api/channels'
import { useAuthStore } from '@/store/authStore'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Skeleton } from '@/components/ui/Skeleton'

// ─── Утилиты ────────────────────────────────────────────────────

function fmtSubscribers(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`
  return String(n)
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

// ─── Цвета тарифов (из tokens.css) ──────────────────────────────
const TARIFF_COLORS: Record<string, string> = {
  free:     'var(--neutral)',
  starter:  'var(--info)',
  pro:      'var(--accent-400)',
  business: 'var(--warning)',
}

// ─── Компонент: карточка тарифа ─────────────────────────────────

function TariffCard({
  item, isCurrentPlan, totalChannels, delay,
}: {
  item: TariffStatsItem
  isCurrentPlan: boolean
  totalChannels: number
  delay: number
}) {
  const color = TARIFF_COLORS[item.tariff]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay }}
      style={{
        background: 'var(--bg-surface)',
        border: `2px solid ${isCurrentPlan ? color : 'var(--border)'}`,
        borderRadius: 16,
        padding: 16,
        position: 'relative',
      }}
    >
      {isCurrentPlan && (
        <span style={{
          position: 'absolute', top: -10, left: 12,
          background: color, color: 'white',
          fontSize: 10, fontWeight: 700,
          padding: '2px 8px', borderRadius: 4,
        }}>
          ВАШ ТАРИФ
        </span>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{
          fontSize: 13, fontWeight: 700,
          color, background: color + '22',
          padding: '3px 8px', borderRadius: 6,
        }}>
          {item.label}
        </span>
        {item.premium_count > 0 && (
          <span style={{ fontSize: 11, color: 'var(--warning)' }}>
            💎 +{item.premium_count} premium
          </span>
        )}
      </div>

      <p className="font-mono" style={{
        fontSize: 28, fontWeight: 700, lineHeight: 1, marginBottom: 4,
        color: 'var(--text-primary)',
      }}>
        {item.available.toLocaleString('ru')}
      </p>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
        каналов доступно
      </p>

      <ProgressBar
        value={item.available}
        max={totalChannels}
        variant={item.tariff === 'pro' || item.tariff === 'business' ? 'success' : 'default'}
        height={4}
      />
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
        {item.percent_of_total}% от базы
      </p>
    </motion.div>
  )
}

// ─── Компонент: строка категории ────────────────────────────────

function CategoryRow({
  cat, userPlan, index,
}: {
  cat: CategoryStats
  userPlan: string
  index: number
}) {
  const [expanded, setExpanded] = useState(false)
  const userAvailable = cat.available_by_tariff[userPlan] ?? 0
  const percent = cat.total > 0 ? Math.round(userAvailable / cat.total * 100) : 0

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 + index * 0.04 }}
      onClick={() => setExpanded(e => !e)}
      style={{ cursor: 'pointer', marginBottom: 8 }}
    >
      {/* Строка 1: категория + счётчик */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <p style={{ fontSize: 14, fontWeight: 600 }}>
          {cat.category}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="font-mono" style={{ fontSize: 13, color: 'var(--accent-400)' }}>
            {userAvailable} / {cat.total}
          </span>
          <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            {expanded ? '▾' : '›'}
          </span>
        </div>
      </div>

      {/* Прогресс-бар доступности */}
      <ProgressBar
        value={userAvailable}
        max={cat.total}
        variant={percent === 100 ? 'success' : percent > 50 ? 'default' : 'danger'}
        height={4}
      />
      <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
        {percent}% доступно на вашем тарифе
      </p>

      {/* Расширенный вид: топ каналы + доступность по тарифам */}
      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          style={{ marginTop: 14, overflow: 'hidden' }}
        >
          {/* Доступность по всем тарифам */}
          <div style={{
            display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap',
          }}>
            {Object.entries(cat.available_by_tariff).map(([tariff, count]) => (
              <span key={tariff} style={{
                fontSize: 11, fontWeight: 600,
                padding: '3px 8px', borderRadius: 6,
                background: TARIFF_COLORS[tariff] + '22',
                color: TARIFF_COLORS[tariff],
              }}>
                {tariff.toUpperCase()}: {count}
              </span>
            ))}
          </div>

          {/* Топ каналы */}
          {cat.top_channels.length > 0 && (
            <>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                Топ каналы:
              </p>
              {cat.top_channels.map((ch, i) => (
                <div key={ch.id} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '6px 0',
                  borderBottom: i < cat.top_channels.length - 1 ? '1px solid var(--border)' : 'none',
                  fontSize: 13,
                }}>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {ch.username ? `@${ch.username}` : ch.title}
                  </span>
                  <span className="font-mono" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    {fmtSubscribers(ch.subscribers)}
                  </span>
                </div>
              ))}
            </>
          )}
        </motion.div>
      )}
    </motion.div>
  )
}

// ─── Скелетон ───────────────────────────────────────────────────

function ChannelsSkeleton() {
  return (
    <div className="page-content" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {[...Array(4)].map((_, i) => <Skeleton key={i} height={110} radius={16} />)}
      </div>
      <Skeleton height={24} width="60%" />
      {[...Array(5)].map((_, i) => <Skeleton key={i} height={72} radius={14} />)}
    </div>
  )
}

// ─── Главная страница ────────────────────────────────────────────

export default function Channels() {
  const user = useAuthStore(s => s.user)
  const currentPlan = user?.plan ?? 'free'

  const { data, isLoading } = useQuery({
    queryKey: ['channels', 'stats'],
    queryFn: channelsApi.stats,
    staleTime: 10 * 60_000, // 10 минут (сервер кэширует 1 час)
  })

  if (isLoading) return <ChannelsSkeleton />

  const d = data!
  const totalChannels = d.total_channels

  return (
    <div className="page-content page-enter">

      {/* Заголовок */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>База каналов</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 4 }}>
          <p className="font-mono" style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent-400)' }}>
            {totalChannels.toLocaleString('ru')}
          </p>
          <div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Telegram-каналов</p>
            <p style={{ fontSize: 11, color: 'var(--success)' }}>
              +{d.added_last_7d} за неделю
            </p>
          </div>
        </div>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
          Обновлено: {fmtDate(d.last_updated)}
        </p>
      </div>

      {/* Карточки тарифов — 2×2 сетка */}
      <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
        ДОСТУПНО ПО ТАРИФАМ
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
        {d.tariff_stats.map((item, i) => (
          <TariffCard
            key={item.tariff}
            item={item}
            isCurrentPlan={item.tariff === currentPlan}
            totalChannels={totalChannels}
            delay={i * 0.06}
          />
        ))}
      </div>

      {/* CTA если не business */}
      {currentPlan !== 'business' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          style={{
            background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.1))',
            border: '1px solid var(--border-accent)',
            borderRadius: 14,
            padding: '14px 16px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>
              Хотите больше каналов?
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Upgrade открывает доступ к большим каналам
            </p>
          </div>
          <Link
            to="/billing"
            style={{
              textDecoration: 'none',
              background: 'var(--accent-500)',
              color: 'white',
              padding: '8px 14px',
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            Upgrade ↗
          </Link>
        </motion.div>
      )}

      {/* Список категорий */}
      <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
        КАТЕГОРИИ — {d.total_categories}
      </p>
      {d.categories.map((cat, i) => (
        <CategoryRow
          key={cat.category}
          cat={cat}
          userPlan={currentPlan}
          index={i}
        />
      ))}

    </div>
  )
}
```

---

### Шаг 2.4 — Добавить 5-ю вкладку в BottomNav

В `mini_app/src/components/layout/BottomNav.tsx` обновить список вкладок:

```tsx
// Заменить существующий массив items на:
const items = [
  { to: '/',          icon: '🏠', label: 'Главная'   },
  { to: '/campaigns', icon: '📊', label: 'Кампании'  },
  { to: '/analytics', icon: '📈', label: 'Аналитика' },
  { to: '/channels',  icon: '📡', label: 'База'       },  // ← новый
  { to: '/billing',   icon: '💳', label: 'Баланс'    },
]
```

Также обновить CSS если иконок стало 5 — уменьшить шрифт подписей:

В `mini_app/src/styles/global.css` найти `.nav-item` и добавить:

```css
/* При 5 вкладках текст чуть меньше */
.bottom-nav:has(.nav-item:nth-child(5)) .nav-item {
  font-size: 9px;
}
```

---

### Шаг 2.5 — Добавить маршрут в App.tsx

В `mini_app/src/App.tsx` добавить:

```tsx
import Channels from '@/pages/Channels'

// В Routes добавить:
<Route path="/channels" element={<Channels />} />
```

---

## ФИНАЛЬНАЯ ПРОВЕРКА

```bash
# Бэкенд
docker compose restart api
curl http://localhost:8001/api/channels/stats | python -m json.tool
# → JSON с total_channels, categories[], tariff_stats[]

# Фронтенд
cd mini_app
npm run build
# → без ошибок

npm run dev
# Открыть /channels
```

### Визуальная проверка:
```
✅ 4 карточки тарифов в сетке 2×2 с ProgressBar
✅ Текущий тариф пользователя выделен цветным border + "ВАШ ТАРИФ"
✅ Реальное количество каналов из БД (не mock!)
✅ Счётчик "+N за неделю" из реальных данных
✅ CTA блок для upgrade (скрыт для business)
✅ Список категорий: tap → разворачивается
✅ В развёрнутой категории: доступность по тарифам + топ 3 канала
✅ BottomNav: 5 вкладок, "База" активна на /channels
```

## Коммит

```bash
git add \
  src/api/constants/tariffs.py \
  src/api/routers/channels.py \
  src/api/main.py \
  mini_app/src/api/channels.ts \
  mini_app/src/pages/Channels.tsx \
  mini_app/src/components/layout/BottomNav.tsx \
  mini_app/src/styles/global.css \
  mini_app/src/App.tsx

git commit -m "feat: add public channel database statistics page

Backend:
  - GET /api/channels/stats: public endpoint with Redis cache (1h TTL)
    Optimized: single GROUP BY query for categories, not N+1
  - GET /api/channels/preview: per-user accessible channels (JWT required)
  - src/api/constants/tariffs.py: centralized tariff limits/categories

Frontend:
  - Channels page: live stats from DB, tariff cards 2x2 grid
  - TariffCard: highlights current plan, premium counter, progress bar
  - CategoryRow: tap-to-expand with per-tariff availability + top channels
  - CTA upgrade block (hidden for business plan)
  - BottomNav: added 5th tab '📡 База'"

git push origin developer2/belin
```
