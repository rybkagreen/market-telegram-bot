# 📊 План: Публичная статистика наполнения базы каналов

## 🎯 Цель

Повысить прозрачность и мотивировать upgrade тарифов через отображение:
1. Общего количества каналов в базе
2. Распределения по категориям
3. Доступности каналов для каждого тарифа

---

## 1. 📁 Структура данных

### Backend API

```python
# src/api/routers/channels.py

class CategoryStats(BaseModel):
    """Статистика по категории."""
    category: str
    category_name: str
    total_channels: int
    available_by_tariff: dict[str, int]  # {tariff: count}
    top_channels: list[dict]  # Топ-3 канала


class DatabaseStats(BaseModel):
    """Общая статистика базы каналов."""
    total_channels: int
    total_categories: int
    last_updated: datetime
    categories: list[CategoryStats]
    tariff_summary: dict[str, TariffSummary]


class TariffSummary(BaseModel):
    """Сводка по тарифу."""
    tariff: str
    tariff_name: str
    price: int
    total_available_channels: int
    percent_of_total: float
    premium_channels_count: int
    categories_available: list[str]


@router.get("/channels/stats", response_model=DatabaseStats)
async def get_channel_stats():
    """
    Получить статистику наполнения базы каналов.
    Доступно ВСЕМ пользователям (даже без авторизации).
    """
    async with async_session_factory() as session:
        # Общая статистика
        total = await session.execute(select(func.count(TelegramChat.id)))
        total_channels = total.scalar()
        
        # Статистика по категориям
        categories = []
        for category, category_name in EXPANDED_CATEGORIES.items():
            # Всего каналов в категории
            cat_total = await session.execute(
                select(func.count(TelegramChat.id))
                .where(TelegramChat.primary_category == category)
            )
            cat_count = cat_total.scalar()
            
            # Доступно по тарифам
            available_by_tariff = {
                "free": await get_available_for_tariff(session, category, "free"),
                "starter": await get_available_for_tariff(session, category, "starter"),
                "pro": await get_available_for_tariff(session, category, "pro"),
                "business": await get_available_for_tariff(session, category, "business"),
            }
            
            # Топ-3 канала
            top_channels = await get_top_channels_in_category(session, category, limit=3)
            
            categories.append(CategoryStats(
                category=category,
                category_name=category_name,
                total_channels=cat_count,
                available_by_tariff=available_by_tariff,
                top_channels=top_channels,
            ))
        
        # Сводка по тарифам
        tariff_summary = {}
        for tariff_code, tariff_data in TARIFFS.items():
            total_available = await get_total_available_for_tariff(session, tariff_code)
            
            tariff_summary[tariff_code] = TariffSummary(
                tariff=tariff_code,
                tariff_name=tariff_data["name"],
                price=tariff_data["price_month"],
                total_available_channels=total_available,
                percent_of_total=round(total_available / total_channels * 100, 1) if total_channels > 0 else 0,
                premium_channels_count=await get_premium_channels_count(session, tariff_code),
                categories_available=tariff_data.get("channel_categories", []),
            )
        
        return DatabaseStats(
            total_channels=total_channels,
            total_categories=len(EXPANDED_CATEGORIES),
            last_updated=datetime.now(),
            categories=categories,
            tariff_summary=tariff_summary,
        )
```

---

## 2. 📱 UI/UX (Mini App)

### Страница "База каналов"

```typescript
// mini_app/src/pages/ChannelsDatabase.tsx

export default function ChannelsDatabase() {
  const { data: stats } = useQuery({
    queryKey: ['channels-stats'],
    queryFn: () => channelsApi.getStats(),
  });

  return (
    <div className="page-content">
      {/* Заголовок */}
      <div className="stats-header">
        <h1>📊 База каналов</h1>
        <p className="subtitle">
          Актуальная статистика наполнения базы
        </p>
        <p className="last-updated">
          Обновлено: {formatDate(stats.last_updated)}
        </p>
      </div>

      {/* Общая статистика */}
      <div className="stats-cards">
        <StatCard
          icon="📺"
          value={stats.total_channels.toLocaleString()}
          label="Всего каналов"
        />
        <StatCard
          icon="📁"
          value={stats.total_categories}
          label="Категорий"
        />
        <StatCard
          icon="📈"
          value="+1,234"
          label="За неделю"
          trend="up"
        />
      </div>

      {/* Сводка по тарифам */}
      <div className="tariff-summary">
        <h2>🎫 Доступно по тарифам</h2>
        
        <div className="tariff-cards">
          {Object.values(stats.tariff_summary).map((tariff) => (
            <TariffCard
              key={tariff.tariff}
              tariff={tariff}
              isCurrent={user.tariff === tariff.tariff}
              onUpgrade={() => navigateToBilling()}
            />
          ))}
        </div>
      </div>

      {/* Категории */}
      <div className="categories-list">
        <h2>📁 Категории каналов</h2>
        
        {stats.categories.map((category) => (
          <CategoryRow
            key={category.category}
            category={category}
            userTariff={user.tariff}
          />
        ))}
      </div>
    </div>
  );
}
```

### Компонент TariffCard

```typescript
interface TariffCardProps {
  tariff: TariffSummary;
  isCurrent: boolean;
  onUpgrade: () => void;
}

function TariffCard({ tariff, isCurrent, onUpgrade }: TariffCardProps) {
  return (
    <div className={`tariff-card ${tariff.tariff} ${isCurrent ? 'current' : ''}`}>
      <div className="tariff-header">
        <h3>{tariff.tariff_name}</h3>
        {tariff.tariff === 'business' && <span className="badge">💎 Premium</span>}
        {tariff.tariff === 'pro' && <span className="badge">⭐ Популярный</span>}
      </div>
      
      <div className="tariff-price">
        {tariff.price === 0 ? 'Бесплатно' : `${tariff.price.toLocaleString()}₽/мес`}
      </div>
      
      <div className="tariff-stats">
        <div className="stat">
          <span className="value">{tariff.total_available_channels.toLocaleString()}</span>
          <span className="label">каналов доступно</span>
        </div>
        
        <div className="stat">
          <span className="value">{tariff.percent_of_total}%</span>
          <span className="label">от общей базы</span>
        </div>
        
        {tariff.premium_channels_count > 0 && (
          <div className="stat">
            <span className="value">+{tariff.premium_channels_count}</span>
            <span className="label">Premium каналов</span>
          </div>
        )}
      </div>
      
      <div className="tariff-categories">
        <span className="label">Категории:</span>
        <div className="categories-tags">
          {tariff.categories_available.slice(0, 3).map(cat => (
            <span key={cat} className="tag">{getCategoryName(cat)}</span>
          ))}
          {tariff.categories_available.length > 3 && (
            <span className="tag more">+{tariff.categories_available.length - 3}</span>
          )}
        </div>
      </div>
      
      {!isCurrent && tariff.tariff !== 'free' && (
        <button className="btn-upgrade" onClick={onUpgrade}>
          {tariff.tariff === 'business' ? '🚀 Перейти на Business' : '⬆️ Upgrade'}
        </button>
      )}
      
      {isCurrent && (
        <div className="current-tariff-badge">
          ✅ Ваш текущий тариф
        </div>
      )}
    </div>
  );
}
```

### Компонент CategoryRow

```typescript
interface CategoryRowProps {
  category: CategoryStats;
  userTariff: string;
}

function CategoryRow({ category, userTariff }: CategoryRowProps) {
  const availableCount = category.available_by_tariff[userTariff];
  const totalCount = category.total_channels;
  const percent = Math.round(availableCount / totalCount * 100);
  
  const isFullyAvailable = percent === 100;
  const isPartiallyAvailable = percent > 0 && percent < 100;
  const isNotAvailable = percent === 0;
  
  return (
    <div className="category-row">
      <div className="category-info">
        <div className="category-name">
          {category.category_name}
          {category.total_channels > 1000 && <span className="badge-hot">🔥 Популярная</span>}
        </div>
        <div className="category-stats">
          <span className="total">{totalCount.toLocaleString()} каналов</span>
        </div>
      </div>
      
      <div className="category-availability">
        {isFullyAvailable && (
          <div className="availability-badge available">
            ✅ Все каналы доступны
          </div>
        )}
        
        {isPartiallyAvailable && (
          <div className="availability-bar">
            <div 
              className="bar-fill" 
              style={{ width: `${percent}%` }}
            />
            <div className="bar-text">
              {availableCount.toLocaleString()} из {totalCount.toLocaleString()} 
              ({percent}%)
            </div>
            <div className="bar-lock">
              🔒 {totalCount - availableCount} на других тарифах
            </div>
          </div>
        )}
        
        {isNotAvailable && (
          <div className="availability-badge locked">
            🔒 Недоступно на вашем тарифе
          </div>
        )}
      </div>
      
      {/* Топ-3 канала */}
      <div className="top-channels-preview">
        <span className="label">Топ каналы:</span>
        <div className="channels-list">
          {category.top_channels.map((channel, i) => (
            <div key={channel.id} className="channel-item">
              <span className="rank">#{i + 1}</span>
              <span className="name">{channel.title}</span>
              <span className="subscribers">{channel.subscribers.toLocaleString()} 👥</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Кнопка upgrade если частично доступно */}
      {isPartiallyAvailable && (
        <button className="btn-unlock">
          🔓 Разблокировать все {totalCount - availableCount} каналов
        </button>
      )}
    </div>
  );
}
```

---

## 3. 🎨 Визуальный дизайн

### Цветовая схема

```css
/* Статусы доступности */
.availability-badge.available {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 600;
}

.availability-badge.locked {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 600;
}

/* Прогресс бар */
.availability-bar {
  position: relative;
  height: 60px;
  background: #f3f4f6;
  border-radius: 12px;
  overflow: hidden;
}

.bar-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
  transition: width 0.5s ease;
}

.bar-text {
  position: absolute;
  top: 8px;
  left: 12px;
  font-weight: 600;
  color: #1f2937;
}

.bar-lock {
  position: absolute;
  bottom: 8px;
  left: 12px;
  font-size: 12px;
  color: #6b7280;
}

/* Карточки тарифов */
.tariff-card {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 16px;
  padding: 24px;
  transition: all 0.3s ease;
}

.tariff-card.pro {
  border-color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
}

.tariff-card.business {
  border-color: #f59e0b;
  box-shadow: 0 4px 6px -1px rgba(245, 158, 11, 0.2);
}

.tariff-card.current {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-color: #0ea5e9;
}
```

---

## 4. 📊 Пример данных API

```json
{
  "total_channels": 15847,
  "total_categories": 10,
  "last_updated": "2026-03-02T14:30:00Z",
  "categories": [
    {
      "category": "business",
      "category_name": "Бизнес и финансы",
      "total_channels": 2345,
      "available_by_tariff": {
        "free": 234,
        "starter": 892,
        "pro": 1876,
        "business": 2345
      },
      "top_channels": [
        {
          "id": 1,
          "title": "Тинькофф Журнал",
          "subscribers": 890000,
          "er_rate": 4.2,
          "overall_rating": 8.9
        },
        {
          "id": 2,
          "title": "Секрет фирмы",
          "subscribers": 650000,
          "er_rate": 3.8,
          "overall_rating": 8.5
        },
        {
          "id": 3,
          "title": "Forbes Russia",
          "subscribers": 2500000,
          "er_rate": 5.1,
          "overall_rating": 9.5,
          "is_premium": true
        }
      ]
    }
  ],
  "tariff_summary": {
    "free": {
      "tariff": "free",
      "tariff_name": "Free",
      "price": 0,
      "total_available_channels": 1234,
      "percent_of_total": 7.8,
      "premium_channels_count": 0,
      "categories_available": ["business", "marketing"]
    },
    "starter": {
      "tariff": "starter",
      "tariff_name": "Starter",
      "price": 990,
      "total_available_channels": 5678,
      "percent_of_total": 35.8,
      "premium_channels_count": 0,
      "categories_available": ["business", "marketing", "it", "finance", "ecommerce"]
    },
    "pro": {
      "tariff": "pro",
      "tariff_name": "Pro",
      "price": 2990,
      "total_available_channels": 12456,
      "percent_of_total": 78.6,
      "premium_channels_count": 0,
      "categories_available": "all_except_premium"
    },
    "business": {
      "tariff": "business",
      "tariff_name": "Business",
      "price": 9990,
      "total_available_channels": 15847,
      "percent_of_total": 100.0,
      "premium_channels_count": 47,
      "categories_available": "all"
    }
  }
}
```

---

## 5. 🔧 Backend реализация

### Helper функции

```python
# src/api/helpers/channel_stats.py

async def get_available_for_tariff(
    session: AsyncSession,
    category: str,
    tariff: str
) -> int:
    """Получить количество доступных каналов для тарифа в категории."""
    tariff_limits = TARIFFS[tariff]
    
    query = select(func.count(TelegramChat.id)).where(
        TelegramChat.primary_category == category,
        TelegramChat.is_active == True,
        TelegramChat.is_scam == False,
        TelegramChat.is_fake == False,
    )
    
    # Ограничение по подписчикам
    if tariff_limits["channel_max_subscribers"] != -1:
        query = query.where(
            TelegramChat.subscribers <= tariff_limits["channel_max_subscribers"]
        )
    
    # Ограничение по рейтингу
    if tariff_limits.get("channel_min_rating", 0) > 0:
        query = query.where(
            TelegramChat.overall_rating >= tariff_limits["channel_min_rating"]
        )
    
    # Ограничение по категориям
    categories = tariff_limits.get("channel_categories", [])
    if categories != "all" and categories != "all_except_premium":
        query = query.where(
            TelegramChat.primary_category.in_(categories)
        )
    
    result = await session.execute(query)
    return result.scalar() or 0


async def get_top_channels_in_category(
    session: AsyncSession,
    category: str,
    limit: int = 3
) -> list[dict]:
    """Получить топ каналов в категории."""
    query = (
        select(
            TelegramChat.id,
            TelegramChat.title,
            TelegramChat.subscribers,
            TelegramChat.er_rate,
            TelegramChat.overall_rating,
        )
        .where(
            TelegramChat.primary_category == category,
            TelegramChat.is_active == True,
        )
        .order_by(TelegramChat.subscribers.desc())
        .limit(limit)
    )
    
    result = await session.execute(query)
    channels = []
    for row in result.all():
        channels.append({
            "id": row.id,
            "title": row.title,
            "subscribers": row.subscribers,
            "er_rate": row.er_rate,
            "overall_rating": row.overall_rating,
            "is_premium": row.subscribers > 1000000,  # Пример критерия premium
        })
    return channels


async def get_premium_channels_count(
    session: AsyncSession,
    tariff: str
) -> int:
    """Получить количество premium каналов для тарифа."""
    if tariff != "business":
        return 0
    
    query = select(func.count(TelegramChat.id)).where(
        TelegramChat.subscribers > 1000000,  # Premium критерий
        TelegramChat.is_active == True,
    )
    
    result = await session.execute(query)
    return result.scalar() or 0
```

---

## 6. 📱 Мобильная адаптация

```css
/* Адаптация под мобильные */
@media (max-width: 768px) {
  .tariff-cards {
    flex-direction: column;
    gap: 16px;
  }
  
  .category-row {
    flex-direction: column;
    gap: 12px;
  }
  
  .availability-bar {
    height: 80px;
  }
  
  .top-channels-preview {
    font-size: 14px;
  }
}

/* Анимации */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.category-row {
  animation: slideIn 0.3s ease-out;
}

/* Темная тема */
@media (prefers-color-scheme: dark) {
  .tariff-card {
    background: #1f2937;
    border-color: #374151;
  }
  
  .bar-fill {
    background: linear-gradient(90deg, #60a5fa 0%, #3b82f6 100%);
  }
}
```

---

## 7. 🚀 Эффект от внедрения

### Ожидаемые метрики

```python
EXPECTED_IMPROVEMENTS = {
    # Конверсия в платные тарифы
    "free_to_starter_conversion": {
        "before": 0.05,
        "after": 0.12,
        "improvement": "+140%",
    },
    "free_to_pro_conversion": {
        "before": 0.02,
        "after": 0.06,
        "improvement": "+200%",
    },
    "starter_to_pro_conversion": {
        "before": 0.08,
        "after": 0.18,
        "improvement": "+125%",
    },
    "pro_to_business_conversion": {
        "before": 0.03,
        "after": 0.07,
        "improvement": "+133%",
    },
    
    # Вовлеченность
    "page_views_database_stats": {
        "target": 0.65,  # 65% пользователей посмотрят статистику
    },
    "tariff_comparison_clicks": {
        "target": 0.45,  # 45% будут сравнивать тарифы
    },
    
    # Revenue
    "monthly_recurring_revenue": {
        "before": 500000,
        "after": 850000,
        "improvement": "+70%",
    },
}
```

---

## 8. ✅ Чеклист реализации

### Backend (3-4 дня)
- [ ] Создать модель `ChannelAnalytics`
- [ ] Добавить endpoint `/api/channels/stats`
- [ ] Реализовать helper функции
- [ ] Добавить кэширование (Redis, TTL=1 час)
- [ ] Написать unit-тесты

### Frontend Mini App (4-5 дней)
- [ ] Создать страницу `ChannelsDatabase`
- [ ] Компонент `TariffCard`
- [ ] Компонент `CategoryRow`
- [ ] Компонент `StatCard`
- [ ] Адаптация под мобильные
- [ ] Темная тема

### Интеграция (2 дня)
- [ ] Подключить реальные данные
- [ ] Протестировать на разных тарифах
- [ ] Оптимизировать производительность
- [ ] Добавить аналитику (клики, конверсии)

### Маркетинг (1 день)
- [ ] Добавить баннер в главном меню
- [ ] Email рассылка пользователям
- [ ] Пост в Telegram канале
- [ ] A/B тестирование CTA

**Итого: 10-12 дней**

---

## 💡 Заключение

Публичная статистика наполнения базы:

1. **Прозрачность** — пользователь видит за что платит
2. **Мотивация** — наглядно показывает преимущества upgrade
3. **Доверие** — открытость данных повышает лояльность
4. **Конверсия** — ожидаемый рост +70-140% в платные тарифы

**Рекомендация:** Реализовать в первую очередь, так как это усилит эффективность всех остальных улучшений из основного плана!
