# 📊 Расширение аналитики и тарифной сетки Market Telegram Bot

## 🎯 Цель

Увеличить конверсию в платные тарифы через:
1. Более точный таргетинг по категориям
2. Расширенную аналитику каналов
3. Прозрачное разграничение возможностей тарифов
4. AI-аналитику для платных пользователей

---

## 1. 📁 Расширенная структура категорий

### Текущая структура (ограничения)
```python
# Сейчас: ~20 базовых категорий
topics = ["бизнес", "маркетинг", "it", "финансы", ...]
```

### Новая структура (детализированная)

```python
EXPANDED_CATEGORIES = {
    # Бизнес и финансы (8 подкатегорий)
    "business": {
        "startup": "Стартапы и инновации",
        "investments": "Инвестиции и трейдинг",
        "crypto": "Криптовалюты и блокчейн",
        "small_business": "Малый бизнес и ИП",
        "franchise": "Франчайзинг",
        "real_estate_invest": "Инвестиции в недвижимость",
        "stock_market": "Фондовый рынок",
        "personal_finance": "Личные финансы",
    },
    
    # Маркетинг и продажи (7 подкатегорий)
    "marketing": {
        "digital_marketing": "Digital-маркетинг",
        "smm": "SMM и соцсети",
        "target_ads": "Таргетированная реклама",
        "context_ads": "Контекстная реклама",
        "influencer_marketing": "Инфлюенс-маркетинг",
        "email_marketing": "Email-маркетинг",
        "sales_funnel": "Воронки продаж",
    },
    
    # IT и технологии (10 подкатегорий)
    "it": {
        "programming": "Программирование",
        "web_dev": "Веб-разработка",
        "mobile_dev": "Мобильная разработка",
        "ai_ml": "ИИ и машинное обучение",
        "data_science": "Data Science",
        "devops": "DevOps и облака",
        "cybersecurity": "Кибербезопасность",
        "gamedev": "Разработка игр",
        "design_ui_ux": "Дизайн и UI/UX",
        "crypto_tech": "Блокчейн-технологии",
    },
    
    # Образование (6 подкатегорий)
    "education": {
        "online_courses": "Онлайн-курсы",
        "languages": "Изучение языков",
        "school_education": "Школьное образование",
        "university": "Высшее образование",
        "professional_dev": "Профессии и переквалификация",
        "children_education": "Детское образование",
    },
    
    # Здоровье и спорт (7 подкатегорий)
    "health": {
        "fitness": "Фитнес и бодибилдинг",
        "yoga_pilates": "Йога и пилатес",
        "nutrition": "Питание и диеты",
        "mental_health": "Психическое здоровье",
        "medicine": "Медицина и здоровье",
        "beauty": "Красота и косметология",
        "sports_pro": "Профессиональный спорт",
    },
    
    # E-commerce (5 подкатегорий)
    "ecommerce": {
        "online_stores": "Интернет-магазины",
        "marketplaces": "Маркетплейсы",
        "dropshipping": "Дропшиппинг",
        "fashion_retail": "Мода и одежда",
        "electronics": "Электроника и техника",
    },
    
    # Развлечения (6 подкатегорий)
    "entertainment": {
        "movies_series": "Кино и сериалы",
        "music": "Музыка",
        "books": "Книги и литература",
        "games": "Игры и гейминг",
        "humor": "Юмор и мемы",
        "celebrities": "Знаменитости и шоу-бизнес",
    },
    
    # Путешествия (5 подкатегорий)
    "travel": {
        "tourism": "Туризм и отдых",
        "budget_travel": "Бюджетные путешествия",
        "luxury_travel": "Люксовый отдых",
        "business_travel": "Командировки",
        "extreme_travel": "Экстремальный туризм",
    },
    
    # Недвижимость (4 подкатегории)
    "real_estate": {
        "rent": "Аренда жилья",
        "sale": "Продажа недвижимости",
        "commercial": "Коммерческая недвижимость",
        "construction": "Строительство и ремонт",
    },
    
    # Авто (5 подкатегорий)
    "auto": {
        "cars_sale": "Продажа авто",
        "auto_service": "Автосервис и запчасти",
        "motorcycles": "Мотоциклы",
        "auto_news": "Автоновости",
        "driving": "Вождение и ПДД",
    },
}

# Итого: 63 подкатегории вместо ~20
```

---

## 2. 📈 Расширенная аналитика каналов

### Новая модель данных

```python
class ChannelAnalytics(Base):
    """Расширенная аналитика Telegram-канала."""
    
    __tablename__ = "channel_analytics"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    
    # === Базовые метрики ===
    subscribers = Column(Integer, default=0)
    subscribers_growth_7d = Column(Integer, default=0)  # Прирост за 7 дней
    subscribers_growth_30d = Column(Integer, default=0)  # Прирост за 30 дней
    
    # === Вовлеченность ===
    avg_views = Column(Integer, default=0)  # Средние просмотры поста
    avg_reactions = Column(Integer, default=0)  # Средние реакции
    avg_comments = Column(Integer, default=0)  # Средние комментарии
    avg_shares = Column(Integer, default=0)  # Средние репосты
    
    # === Рассчитанные метрики ===
    er_rate = Column(Float, default=0.0)  # Engagement Rate = (реакции + комментарии) / подписчики * 100
    view_rate = Column(Float, default=0.0)  # View Rate = просмотры / подписчики * 100
    viral_coefficient = Column(Float, default=0.0)  # Вирусность = репосты / просмотры * 100
    
    # === Активность ===
    posts_per_day = Column(Float, default=0.0)  # Постов в день
    posts_per_week = Column(Float, default=0.0)  # Постов в неделю
    best_posting_hour = Column(Integer, default=12)  # Лучший час для постинга
    best_posting_day = Column(String(10), default="Monday")  # Лучший день
    
    # === Качество аудитории ===
    audience_quality_score = Column(Float, default=0.0)  # 0-100
    fake_followers_percent = Column(Float, default=0.0)  # Процент ботов
    audience_geo_top3 = Column(JSON)  # Топ-3 страны/города
    audience_age_groups = Column(JSON)  # Распределение по возрасту
    audience_gender = Column(JSON)  # М/Ж распределение
    
    # === Тематика ===
    primary_category = Column(String(50))  # Основная категория
    secondary_categories = Column(JSON)  # Дополнительные категории
    topics = Column(JSON)  # Ключевые темы канала
    
    # === Реклама ===
    has_ads = Column(Boolean, default=False)  # Есть ли реклама
    ads_per_week = Column(Float, default=0.0)  # Рекламы в неделю
    avg_ad_views = Column(Integer, default=0)  # Просмотры рекламы
    ad_rate = Column(Float, default=0.0)  # % рекламы от общего контента
    
    # === Стоимость ===
    estimated_post_price = Column(Numeric(10, 2))  # Ориентировочная стоимость поста
    price_per_1k_views = Column(Numeric(10, 2))  # Цена за 1000 просмотров
    
    # === Рейтинги ===
    overall_rating = Column(Float, default=0.0)  # Общий рейтинг 0-10
    category_rank = Column(Integer)  # Позиция в категории
    growth_rank = Column(Integer)  # Позиция по росту
    
    # === Временные метки ===
    last_checked = Column(DateTime, default=func.now)
    created_at = Column(DateTime, default=func.now)
    updated_at = Column(DateTime, default=func.now, onupdate=func.now)
```

---

## 3. 🎯 Таргетинг и прозрачность для пользователя

### Интерфейс выбора каналов (Mini App)

```typescript
// API endpoint для предпросмотра каналов
GET /api/channels/preview?category=business&tariff=pro

interface ChannelPreview {
  // Показывается ВСЕМ тарифам
  id: number;
  title: string;
  subscribers: number;
  primaryCategory: string;
  overallRating: number;  // 0-10
  
  // Показывается только PRO/BUSINESS
  avgViews?: number;       // Скрыто для FREE
  erRate?: number;         // Скрыто для FREE
  bestPostingTime?: string; // Скрыто для FREE
  estimatedReach?: number;  // Скрыто для FREE
}
```

### Пример UI (Telegram Mini App)

```
┌─────────────────────────────────────────┐
│ 📊 Каналы для рассылки                  │
│                                         │
│ Категория: [Бизнес ▼]                   │
│ Тариф: [PRO ▼]                          │
├─────────────────────────────────────────┤
│                                         │
│ 🔍 Топ-10 каналов по охвату:            │
│                                         │
│ 1. 🏆 Бизнес Молодой                   │
│    👥 1.2M | ⭐ 9.2 | 📈 85% охват     │
│    ✅ Доступно в вашем тарифе           │
│                                         │
│ 2. 🥈 Тинькофф Журнал                  │
│    👥 890K | ⭐ 8.9 | 📈 78% охват     │
│    ✅ Доступно в вашем тарифе           │
│                                         │
│ 3. 🥉 Секрет фирмы                     │
│    👥 650K | ⭐ 8.5 | 📈 72% охват     │
│    ✅ Доступно в вашем тарифе           │
│                                         │
│ ... еще 7 каналов                       │
│                                         │
│ 🔒 Premium каналы (только BUSINESS):    │
│                                         │
│ • Forbes Russia (2.5M)                 │
│   🔒 Доступно на тарифе BUSINESS        │
│                                         │
│ • РБК Инвестиции (1.8M)                │
│   🔒 Доступно на тарифе BUSINESS        │
│                                         │
├─────────────────────────────────────────┤
│ Итого доступно: 47 каналов             │
│ Ожидаемый охват: 3.2M - 4.1M           │
│                                         │
│ [Подробнее о тарифах] [Начать рассылку]│
└─────────────────────────────────────────┘
```

---

## 4. 💰 Новая тарифная сетка

### Структура тарифов

```python
TARIFFS = {
    "free": {
        "name": "Free",
        "price_month": 0,
        "price_year": 0,
        
        # Ограничения
        "campaigns_per_month": 1,
        "channels_max": 10,
        "channel_categories": ["business", "marketing"],  # Только 2 категории
        "channel_min_rating": 0,  # Любые каналы
        "channel_max_subscribers": 10000,  # Только малые каналы
        
        # Фичи
        "ai_generation": False,
        "ai_analytics": False,
        "detailed_analytics": False,
        "priority_support": False,
        "custom_branding": False,
        
        # Прозрачность
        "description": "Базовый тариф для тестирования",
        "limitations": [
            "Только 2 категории каналов",
            "Каналы до 10K подписчиков",
            "1 кампания в месяц",
            "Базовая аналитика",
        ],
    },
    
    "starter": {
        "name": "Starter",
        "price_month": 990,
        "price_year": 9900,  # ~17% скидка
        
        # Ограничения
        "campaigns_per_month": 5,
        "channels_max": 50,
        "channel_categories": ["business", "marketing", "it", "finance", "ecommerce"],
        "channel_min_rating": 5.0,
        "channel_max_subscribers": 50000,
        
        # Фичи
        "ai_generation": True,
        "ai_generation_limit": 5,  # 5 генераций в месяц
        "ai_analytics": False,
        "detailed_analytics": True,
        "priority_support": False,
        "custom_branding": False,
        
        # Прозрачность
        "description": "Для малого бизнеса и стартапов",
        "benefits": [
            "5 категорий каналов",
            "Каналы до 50K подписчиков",
            "5 кампаний в месяц",
            "AI-генерация текстов (5 раз)",
            "Расширенная аналитика",
        ],
    },
    
    "pro": {
        "name": "Pro",
        "price_month": 2990,
        "price_year": 29900,  # ~17% скидка
        "popular": True,  # Метка "Популярный"
        
        # Ограничения
        "campaigns_per_month": 20,
        "channels_max": 200,
        "channel_categories": "all_except_premium",  # Все кроме premium
        "channel_min_rating": 7.0,
        "channel_max_subscribers": 200000,
        
        # Фичи
        "ai_generation": True,
        "ai_generation_limit": 50,
        "ai_analytics": True,
        "ai_analytics_features": [
            "Анализ эффективности кампании",
            "Рекомендации по улучшению",
            "Прогноз охвата",
            "A/B тестирование",
        ],
        "detailed_analytics": True,
        "priority_support": True,
        "custom_branding": False,
        
        # Прозрачность
        "description": "Для растущего бизнеса",
        "benefits": [
            "Все категории (кроме Premium)",
            "Каналы до 200K подписчиков",
            "20 кампаний в месяц",
            "AI-генерация текстов (50 раз)",
            "AI-аналитика кампаний",
            "Приоритетная поддержка",
            "Топ-10 каналов по охвату",
        ],
        "most_popular": True,
    },
    
    "business": {
        "name": "Business",
        "price_month": 9990,
        "price_year": 99900,  # ~17% скидка
        
        # Ограничения
        "campaigns_per_month": -1,  # Безлимит
        "channels_max": -1,  # Безлимит
        "channel_categories": "all",  # Все категории включая premium
        "channel_min_rating": 0,  # Любые каналы
        "channel_max_subscribers": -1,  # Безлимит
        
        # Фичи
        "ai_generation": True,
        "ai_generation_limit": -1,  # Безлимит
        "ai_analytics": True,
        "ai_analytics_features": [
            "Полный AI-анализ кампаний",
            "Персональные рекомендации",
            "Прогноз ROI",
            "A/B/C/D тестирование",
            "Анализ конкурентов",
            "Оптимизация бюджета",
        ],
        "detailed_analytics": True,
        "priority_support": True,
        "custom_branding": True,
        "personal_manager": True,
        
        # Прозрачность
        "description": "Для крупного бизнеса и агентств",
        "benefits": [
            "ВСЕ каналы включая Premium (Forbes, РБК, etc.)",
            "Безлимитные кампании",
            "Безлимитная AI-генерация",
            "Полная AI-аналитика",
            "Персональный менеджер",
            "Кастомный брендинг",
            "API доступ",
            "White label",
        ],
        "vip": True,
    },
}
```

---

## 5. 🤖 AI-аналитика для платных тарифов

### Отчет для PRO тарифа

```python
class AICampaignReport:
    """AI-аналитика кампании (PRO тариф)."""
    
    def generate_report(self, campaign_id: int) -> dict:
        return {
            "summary": {
                "total_sent": 15420,
                "total_views": 8934,
                "total_clicks": 423,
                "ctr": 4.7,  # Click-through rate
                "conversion_rate": 2.1,
            },
            
            "ai_insights": [
                {
                    "type": "success",
                    "message": "Кампания показала CTR на 23% выше среднего по категории",
                    "recommendation": None,
                },
                {
                    "type": "warning", 
                    "message": "Низкая конверсия в каналах с аудиторией 18-24 лет",
                    "recommendation": "Попробуйте изменить призыв к действию для молодой аудитории",
                },
                {
                    "type": "opportunity",
                    "message": "Каналы категории 'crypto' показали на 45% лучшую конверсию",
                    "recommendation": "Увеличьте долю crypto-каналов в следующей кампании",
                },
            ],
            
            "best_performing_channels": [
                {
                    "channel_name": "Крипто Инсайды",
                    "subscribers": 125000,
                    "views": 8900,
                    "clicks": 534,
                    "ctr": 6.0,
                    "conversion": 3.2,
                },
                # ... еще 9 каналов
            ],
            
            "worst_performing_channels": [
                # ... 5 каналов с худшими результатами
            ],
            
            "optimal_posting_times": {
                "best_hour": 19,  # 19:00
                "best_day": "Wednesday",
                "reasoning": "В это время ваша ЦА наиболее активна",
            },
            
            "budget_optimization": {
                "spent": 15420,
                "estimated_waste": 2340,
                "waste_reason": "15% каналов показали CTR < 1%",
                "recommendation": "Исключите эти каналы из будущих кампаний",
            },
        }
```

### Отчет для BUSINESS тарифа (расширенный)

```python
class AICampaignReportBusiness(AICampaignReport):
    """Расширенная AI-аналитика (BUSINESS тариф)."""
    
    def generate_report(self, campaign_id: int) -> dict:
        base_report = super().generate_report(campaign_id)
        
        base_report.update({
            "competitor_analysis": {
                "your_avg_ctr": 4.7,
                "industry_avg_ctr": 3.2,
                "top_competitor_ctr": 5.8,
                "your_position": "2 из 15 в категории",
                "recommendations": [
                    "Увеличьте бюджет на 20% для обхода конкурента X",
                    "Протестируйте новые креативы в каналах Y, Z",
                ],
            },
            
            "roi_prediction": {
                "current_roi": 2.3,
                "predicted_roi_optimized": 3.1,
                "optimization_steps": [
                    "Исключить 12 каналов с CTR < 1%",
                    "Увеличить бюджет на crypto-каналы на 30%",
                    "Сместить постинг на 19:00-21:00",
                    "A/B тестировать 2 варианта заголовка",
                ],
                "estimated_additional_revenue": 145000,
            },
            
            "audience_insights": {
                "demographics": {
                    "age_groups": {
                        "18-24": {"percent": 15, "conversion": 1.2},
                        "25-34": {"percent": 45, "conversion": 3.4},
                        "35-44": {"percent": 28, "conversion": 2.8},
                        "45+": {"percent": 12, "conversion": 1.5},
                    },
                    "gender": {
                        "male": {"percent": 62, "conversion": 2.5},
                        "female": {"percent": 38, "conversion": 2.1},
                    },
                    "geo_top5": [
                        {"city": "Москва", "percent": 35, "conversion": 3.1},
                        {"city": "Санкт-Петербург", "percent": 18, "conversion": 2.8},
                        # ...
                    ],
                },
                
                "interests": [
                    {"topic": "Криптовалюты", "percent": 45, "conversion": 3.8},
                    {"topic": "Инвестиции", "percent": 38, "conversion": 3.2},
                    # ...
                ],
            },
            
            "next_campaign_plan": {
                "recommended_budget": 25000,
                "recommended_channels": 85,
                "expected_reach": 450000,
                "expected_ctr": 5.2,
                "expected_conversions": 234,
                "confidence_score": 0.87,
            },
        })
        
        return base_report
```

---

## 6. 📊 Дашборд аналитики (Mini App)

### Для PRO тарифа

```typescript
interface ProAnalyticsDashboard {
  // Общая статистика
  totalCampaigns: number;
  totalSpent: number;
  totalReach: number;
  avgCTR: number;
  
  // AI-инсайты
  aiInsights: {
    success: string[];
    warnings: string[];
    opportunities: string[];
  };
  
  // Топ каналы
  topChannels: ChannelPerformance[];
  
  // Рекомендации
  recommendations: string[];
}
```

### Для BUSINESS тарифа

```typescript
interface BusinessAnalyticsDashboard extends ProAnalyticsDashboard {
  // Анализ конкурентов
  competitorAnalysis: {
    yourPosition: number;
    totalCompetitors: number;
    topCompetitors: Competitor[];
  };
  
  // ROI прогноз
  roiPrediction: {
    current: number;
    optimized: number;
    steps: string[];
  };
  
  // Демография
  audienceDemographics: {
    ageGroups: AgeGroup[];
    gender: Gender[];
    geo: Geo[];
  };
  
  // План следующей кампании
  nextCampaignPlan: {
    budget: number;
    channels: number;
    expectedReach: number;
    expectedCTR: number;
    confidence: number;
  };
}
```

---

## 7. 🗄️ Миграции базы данных

```python
# migration_001_add_channel_analytics.py
def upgrade():
    # Расширенная аналитика каналов
    op.add_column('channel_analytics', sa.Column('subscribers_growth_7d', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('subscribers_growth_30d', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('avg_reactions', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('avg_comments', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('avg_shares', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('er_rate', sa.Float()))
    op.add_column('channel_analytics', sa.Column('view_rate', sa.Float()))
    op.add_column('channel_analytics', sa.Column('viral_coefficient', sa.Float()))
    op.add_column('channel_analytics', sa.Column('best_posting_hour', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('best_posting_day', sa.String(10)))
    op.add_column('channel_analytics', sa.Column('audience_quality_score', sa.Float()))
    op.add_column('channel_analytics', sa.Column('fake_followers_percent', sa.Float()))
    op.add_column('channel_analytics', sa.Column('audience_geo_top3', sa.JSON()))
    op.add_column('channel_analytics', sa.Column('audience_age_groups', sa.JSON()))
    op.add_column('channel_analytics', sa.Column('audience_gender', sa.JSON()))
    op.add_column('channel_analytics', sa.Column('ads_per_week', sa.Float()))
    op.add_column('channel_analytics', sa.Column('avg_ad_views', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('ad_rate', sa.Float()))
    op.add_column('channel_analytics', sa.Column('estimated_post_price', sa.Numeric(10, 2)))
    op.add_column('channel_analytics', sa.Column('price_per_1k_views', sa.Numeric(10, 2)))
    op.add_column('channel_analytics', sa.Column('overall_rating', sa.Float()))
    op.add_column('channel_analytics', sa.Column('category_rank', sa.Integer()))
    op.add_column('channel_analytics', sa.Column('growth_rank', sa.Integer()))
    
    # Расширение категорий
    op.alter_column('channel_analytics', 'primary_category',
                    existing_type=sa.String(50),
                    nullable=False)
    op.add_column('channel_analytics', sa.Column('secondary_categories', sa.JSON()))
    op.add_column('channel_analytics', sa.Column('topics', sa.JSON()))
    
    # Индексы для производительности
    op.create_index('ix_channel_analytics_er_rate', 'channel_analytics', ['er_rate'])
    op.create_index('ix_channel_analytics_overall_rating', 'channel_analytics', ['overall_rating'])
    op.create_index('ix_channel_analytics_category', 'channel_analytics', ['primary_category'])

# migration_002_update_user_tariffs.py
def upgrade():
    # Обновление enum тарифов
    op.execute("ALTER TYPE user_plan ADD VALUE 'starter' AFTER 'free'")
    
    # Добавление полей для тарифов
    op.add_column('users', sa.Column('ai_generations_used', sa.Integer(), default=0))
    op.add_column('users', sa.Column('ai_generations_limit', sa.Integer(), default=0))
    op.add_column('users', sa.Column('campaigns_limit_per_month', sa.Integer(), default=1))
    op.add_column('users', sa.Column('channels_limit', sa.Integer(), default=10))
    op.add_column('users', sa.Column('channel_categories_access', sa.JSON(), default=['business', 'marketing']))
    op.add_column('users', sa.Column('channel_max_subscribers', sa.Integer(), default=10000))
```

---

## 8. 📱 UI/UX рекомендации

### Страница выбора тарифа

```
┌─────────────────────────────────────────────────────────┐
│ 💎 Выберите тариф для максимального охвата             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │   FREE      │ │  STARTER    │ │   PRO ⭐    │        │
│ │   0₽        │ │  990₽/мес   │ │  2990₽/мес  │        │
│ ├─────────────┤ ├─────────────┤ ├─────────────┤        │
│ │ ✅ 2 катего│ │ ✅ 5 катего│ │ ✅ 10 катего│        │
│ │ ✅ до 10K   │ │ ✅ до 50K   │ │ ✅ до 200K  │        │
│ │ ✅ 1 кампан│ │ ✅ 5 кампан│ │ ✅ 20 кампан│        │
│ │ ❌ Без AI   │ │ ✅ AI текст│ │ ✅ AI анализ│        │
│ │ ❌ Базовая  │ │ ✅ Расшир.  │ │ ✅ Топ-10   │        │
│ │             │ │ ❌ Без AI   │ │ ❌ Без Premium│       │
│ ├─────────────┤ ├─────────────┤ ├─────────────┤        │
│ │ [Выбрать]   │ │ [Выбрать]   │ │ [Выбрать]   │        │
│ └─────────────┘ └─────────────┘ └─────────────┘        │
│                                                         │
│ ┌─────────────────────────────────────────────────┐    │
│ │              BUSINESS 💎                        │    │
│ │              9990₽/мес                          │    │
│ ├─────────────────────────────────────────────────┤    │
│ │ ✅ ВСЕ категории включая Premium                │    │
│ │ ✅ Безлимитные кампании                         │    │
│ │ ✅ Безлимитная AI-генерация                     │    │
│ │ ✅ Полная AI-аналитика + конкуренты             │    │
│ │ ✅ Персональный менеджер                        │    │
│ │ ✅ API доступ + White label                     │    │
│ ├─────────────────────────────────────────────────┤    │
│ │              [Выбрать]                          │    │
│ └─────────────────────────────────────────────────┘    │
│                                                         │
│ 🔍 Сравнить тарифы подробно →                          │
└─────────────────────────────────────────────────────────┘
```

### Страница предпросмотра каналов

```
┌─────────────────────────────────────────────────────────┐
│ 📊 Доступные каналы для рассылки                        │
│                                                         │
│ Ваш тариф: PRO                                          │
│ Доступно: 200 каналов из 847                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🔍 Фильтры:                                             │
│ [Категория: Все ▼] [Подписчики: до 200K ▼]            │
│ [Рейтинг: от 7.0 ▼] [ER: любой ▼]                     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🏆 Топ-10 каналов по охвату (ваш тариф):               │
│                                                         │
│ 1. Тинькофф Журнал                                     │
│    👥 890K | ⭐ 8.9 | 📈 78% | 💰 15K/пост            │
│    Категория: Финансы | ER: 4.2%                       │
│    ✅ Доступно                                          │
│                                                         │
│ 2. Секрет фирмы                                        │
│    👥 650K | ⭐ 8.5 | 📈 72% | 💰 12K/пост            │
│    Категория: Бизнес | ER: 3.8%                        │
│    ✅ Доступно                                          │
│                                                         │
│ ... еще 8 каналов                                       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🔒 Premium каналы (только BUSINESS):                   │
│                                                         │
│ • Forbes Russia (2.5M)                                 │
│   👥 2.5M | ⭐ 9.5 | 📈 92% | 💰 150K/пост           │
│   🔒 Разблокировать на тарифе BUSINESS                │
│                                                         │
│ • РБК Инвестиции (1.8M)                                │
│   👥 1.8M | ⭐ 9.2 | 📈 88% | 💰 120K/пост           │
│   🔒 Разблокировать на тарифе BUSINESS                │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 📈 Ожидаемые результаты:                               │
│ • Охват: 3.2M - 4.1M                                   │
│ • CTR: 3.5% - 5.2%                                     │
│ • Конверсии: 180 - 340                                 │
│                                                         │
│ [⬆️ Upgrade до BUSINESS для Premium каналов]          │
│ [Начать рассылку]                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 9. 📈 Метрики успеха

### KPI для отслеживания

```python
SUCCESS_METRICS = {
    # Конверсия в платные тарифы
    "free_to_starter_conversion": {"target": 0.15, "current": 0.0},
    "free_to_pro_conversion": {"target": 0.08, "current": 0.0},
    "free_to_business_conversion": {"target": 0.02, "current": 0.0},
    
    # Удержание
    "starter_retention_30d": {"target": 0.60, "current": 0.0},
    "pro_retention_30d": {"target": 0.75, "current": 0.0},
    "business_retention_30d": {"target": 0.90, "current": 0.0},
    
    # Использование фич
    "ai_generation_usage_rate": {"target": 0.70, "current": 0.0},
    "ai_analytics_view_rate": {"target": 0.80, "current": 0.0},
    "channel_preview_view_rate": {"target": 0.65, "current": 0.0},
    
    # Revenue
    "avg_revenue_per_user": {"target": 1500, "current": 0.0},
    "monthly_recurring_revenue": {"target": 500000, "current": 0.0},
}
```

---

## 10. 🚀 План реализации

### Этап 1: База данных (1-2 недели)
- [ ] Миграция `channel_analytics`
- [ ] Расширение категорий
- [ ] Обновление модели `User`

### Этап 2: Backend API (2-3 недели)
- [ ] Endpoints для расширенной аналитики
- [ ] AI-аналитика кампаний
- [ ] Таргетинг по категориям

### Этап 3: Mini App UI (2-3 недели)
- [ ] Страница выбора тарифа
- [ ] Предпросмотр каналов
- [ ] Дашборд аналитики

### Этап 4: AI-аналитика (2-3 недели)
- [ ] Генерация отчетов PRO
- [ ] Генерация отчетов BUSINESS
- [ ] Рекомендательная система

### Этап 5: Тестирование (1 неделя)
- [ ] Unit-тесты
- [ ] Integration-тесты
- [ ] A/B тестирование тарифов

**Итого: 8-12 недель**

---

## 💡 Заключение

Предложенное расширение обеспечит:

1. **Прозрачность** — пользователь видит что получает за каждый тариф
2. **Мотивацию к upgrade** — Premium каналы и AI-аналитика только на платных тарифах
3. **Лучший таргетинг** — 63 подкатегории вместо 20
4. **AI-инсайты** — автоматические рекомендации для улучшения кампаний
5. **Конкурентное преимущество** — полная аналитика + прогнозы ROI
