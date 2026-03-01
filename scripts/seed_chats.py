"""
Скрипт для загрузки начального списка Telegram чатов в БД.
Запускать ПОСЛЕ создания сессии.

Источники чатов:
1. Список из TGStat по тематикам (если TGStatParser работает)
2. Ручной список популярных русскоязычных каналов
3. Поиск через Telethon по ключевым словам
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.db.session import async_session_factory
from src.db.repositories.chat_analytics import ChatAnalyticsRepository


# ─── Расширенный список чатов по тематикам (~1000 каналов) ───────────────────────────────────
SEED_CHATS: dict[str, list[str]] = {

    "IT": [
        # Python
        "python_ru", "pythonist", "django_pythonist", "flask_ru",
        "fastapi_ru", "asyncio_ru", "python_tips", "pythonicway",
        "python_jobs", "pydantic_ru",
        # JavaScript / Frontend
        "javascriptru", "nodejs_ru", "react_js_ru", "vue_js_russia",
        "angular_ru", "typescript_ru", "svelte_ru", "nextjs_ru",
        "frontend_ru", "webdev_ru", "css_ru", "html_ru",
        # Backend / DevOps
        "devops_ru", "kubernetes_ru", "docker_ru", "linux_ru_academy",
        "nginx_ru", "postgresql_ru", "redis_ru", "mongodb_ru",
        "elasticsearch_ru", "kafka_ru", "rabbitmq_ru", "grpc_ru",
        "microservices_ru", "serverless_ru", "terraform_ru", "ansible_ru",
        "ci_cd_ru", "github_ru", "gitlab_ru", "jenkins_ru",
        # Другие языки
        "golang_ru", "rustlang_ru", "kotlin_ru", "swift_ru",
        "java_ru", "scala_ru", "csharp_ru", "cpp_ru",
        "ruby_ru", "php_ru", "laravel_ru", "symfony_ru",
        # Data / AI / ML
        "machinelearning_ru", "neural_network_ru", "AIMLgroup",
        "datascience_ru", "bigdata_ru", "data_analysis_ml",
        "pandas_ru", "pytorch_ru", "tensorflow_ru", "sklearn_ru",
        "nlp_ru", "computer_vision_ru", "rl_ru", "llm_ru",
        "gpt_ru", "stable_diffusion_ru", "mlops_ru",
        # Мобильная разработка
        "android_ru", "ios_ru", "flutter_ru", "react_native_ru",
        "xamarin_ru", "unity3d_ru", "unrealengine_ru", "gamedev_ru",
        # Безопасность / Сети
        "cybersecurity_ru", "pentest_ru", "infosec_ru", "ctf_ru",
        "networking_ru", "sre_ru", "monitoring_ru",
        # Общее IT
        "tproger", "habr_ru", "proglib", "it_jobs_ru",
        "opensource_ru", "sql_ru", "api_design_ru",
        "system_design_ru", "clean_code_ru", "refactoring_ru",
        "algorithms_ru", "leetcode_ru", "competitive_programming_ru",
        "tech_interviews_ru", "remote_jobs_ru", "freelance_dev_ru",
        "startup_tech_ru", "product_management_ru", "ux_ui_ru",
        "figma_ru", "design_systems_ru",
        # Новости IT
        "techcrunch_ru", "vc_ru_tech", "cnews_ru", "habr_news",
        "it_channel_ru", "digital_ru", "ruvds_official",
        "selectel_official", "timeweb_official",
    ],

    "Бизнес": [
        # Предпринимательство
        "businessru", "rusbase", "startupoftheday", "vc_ru",
        "the_bell_io", "roem_ru", "rb_ru", "incru",
        "entrepreneur_ru", "smallbiz_ru", "selfemployed_ru",
        "biznes_online", "biznes_idei_ru", "franchise_ru",
        # Маркетинг / SMM
        "marketingpro_ru", "smmplanner", "targetolog_ru",
        "content_marketing_ru", "email_marketing_ru", "smm_ru",
        "instagram_marketing_ru", "tiktok_marketing_ru",
        "vk_marketing_ru", "telegram_marketing_ru",
        "influencer_ru", "viral_ru", "growth_hacking_ru",
        # SEO / Реклама
        "seo_ru", "contextru", "yandex_direct_ru", "google_ads_ru",
        "seo_tips_ru", "link_building_ru", "analytics_ru",
        "metrika_ru", "ga4_ru", "data_driven_ru",
        # Продажи / CRM
        "sales_ru", "b2b_ru", "b2c_ru", "crmru",
        "amocrm_ru", "bitrix24_ru", "retail_ru",
        "ecommerce_ru", "marketplace_sellers_ru", "wildberries_sellers",
        "ozon_sellers", "avito_business",
        # Финансы бизнеса
        "accounting_ru", "taxes_ru", "ip_ooo_ru",
        "business_finance_ru", "cashflow_ru", "unit_economics_ru",
        "investments_biz_ru", "venture_ru", "grants_ru",
        # HR / Команда
        "hr_ru", "recruiting_ru", "management_ru",
        "leadership_ru", "team_ru", "remote_work_ru",
        "corporate_culture_ru", "burnout_ru",
        # Недвижимость бизнес
        "commercial_estate_ru", "coworking_ru", "office_ru",
        # Право / Документы
        "legal_business_ru", "contracts_ru", "ip_protection_ru",
        # Экспорт / Международный бизнес
        "export_ru", "import_ru", "logistics_ru",
        "customs_ru", "foreign_trade_ru",
    ],

    "Образование": [
        # Платформы
        "stepik_courses", "netologyru", "skillboxru",
        "geekbrains_official", "hexlet_ru", "yandex_practicum",
        "otus_ru", "productstar_ru", "contented_ru",
        # Языки
        "english_for_it", "english_ru", "english_daily_ru",
        "englishgrammar_ru", "english_words_ru", "english_phrases_ru",
        "english_listening_ru", "english_speaking_ru",
        "deutsch_ru", "french_ru", "spanish_ru",
        "chinese_ru", "japanese_ru", "korean_ru",
        # Школьные / ЕГЭ
        "ege_ru", "oge_ru", "math_ege_ru", "physics_ege_ru",
        "chemistry_ege_ru", "biology_ege_ru", "history_ege_ru",
        "russian_ege_ru", "english_ege_ru", "informatics_ege_ru",
        # Университет
        "university_ru", "science_ru", "phd_ru",
        "research_ru", "academic_writing_ru",
        # Математика / Точные науки
        "mathematics_ru", "physics_ru", "chemistry_ru",
        "biology_ru", "astronomy_ru", "statistics_ru",
        # Гуманитарные
        "history_ru", "philosophy_ru", "psychology_courses_ru",
        "sociology_ru", "economics_ru", "political_science_ru",
        "literature_ru", "linguistics_ru",
        # Дополнительное образование
        "drawing_ru", "music_ru", "photography_ru",
        "cooking_ru", "chess_ru", "typing_ru",
        "memory_ru", "speed_reading_ru", "public_speaking_ru",
        # Детское образование
        "kids_education_ru", "preschool_ru", "school_ru",
        "kids_coding_ru", "kids_english_ru",
        # Саморазвитие
        "selfdevelopment_ru", "books_ru", "reading_ru",
        "podcasts_ru", "ted_ru", "lifelong_learning_ru",
        "productivity_ru", "timemanagement_ru", "habits_ru",
    ],

    "Товары": [
        # Маркетплейсы
        "wildberries_official", "ozon_official", "avito_ru",
        "lamoda_ru", "sbermegamarket", "yandex_market_ru",
        # Электроника
        "mvideo_ru", "eldorado_ru", "dns_shop_ru",
        "citilink_ru", "pleer_ru", "re_store_ru",
        "apple_russia", "samsung_russia", "xiaomi_russia",
        "huawei_russia", "honor_russia",
        # Одежда / Мода
        "fashion_ru", "streetwear_ru", "sneakers_ru",
        "luxury_ru", "vintage_ru", "secondhand_ru",
        "zara_russia", "hm_russia", "uniqlo_russia",
        # Дом / Интерьер
        "ikea_ru", "leroy_merlin_ru", "castorama_ru",
        "interior_ru", "home_decor_ru", "furniture_ru",
        "renovation_ru", "garden_ru",
        # Красота / Косметика
        "beauty_ru", "makeup_ru", "skincare_ru",
        "haircare_ru", "perfume_ru", "organic_beauty_ru",
        "letu_ru", "riv_gosh_ru",
        # Спортивные товары
        "sport_goods_ru", "decathlon_russia", "sportmaster_ru",
        "outdoor_ru", "camping_gear_ru", "bicycle_ru",
        # Детские товары
        "kids_toys_ru", "baby_goods_ru", "kids_clothes_ru",
        "mothercare_ru",
        # Авто / Мото
        "auto_parts_ru", "car_accessories_ru", "moto_goods_ru",
        "avtodelo_ru",
        # Книги
        "books_shop_ru", "labirint_ru", "chitai_gorod_ru",
        # Зоотовары
        "pet_goods_ru", "petshop_ru", "zooplus_ru",
        # Продукты / Доставка
        "food_delivery_ru", "yandex_eats_ru", "sbermarket_ru",
        "vkusvill_ru", "magnit_ru",
        # Deals / Скидки
        "deals_ru", "sale_ru", "promo_ru", "cashback_ru",
        "promokod_ru", "aliexpress_deals_ru",
    ],

    "Услуги": [
        # Фриланс биржи
        "freelancehunt_ru", "fl_ru", "kwork_ru",
        "upwork_ru_channel", "fiverr_ru", "youdo_ru",
        "profi_ru", "remontnik_ru", "work_zilla_ru",
        # IT-услуги
        "webstudio_ru", "app_development_ru", "design_studio_ru",
        "seo_agency_ru", "smm_agency_ru", "copywriting_ru",
        "translation_ru", "voice_acting_ru", "video_editing_ru",
        "photography_services_ru",
        # Финансовые услуги
        "accounting_services_ru", "audit_ru", "consulting_ru",
        "financial_advisor_ru", "insurance_ru", "mortgage_ru",
        "credit_ru", "bankiru_channel",
        # Юридические услуги
        "legal_ru", "lawyer_ru", "notary_ru",
        "patent_ru", "trademark_ru", "litigation_ru",
        # Строительство / Ремонт
        "repair_ru", "construction_ru", "architect_ru",
        "plumber_ru", "electrician_ru", "carpenter_ru",
        "painter_ru", "cleaner_ru",
        # Красота / Уход
        "beauty_services_ru", "hairdresser_ru", "nail_ru",
        "massage_ru", "spa_ru", "barbershop_ru",
        # Образовательные услуги
        "tutor_ru", "english_tutor_ru", "math_tutor_ru",
        "driving_school_ru", "music_school_ru",
        # Медицинские услуги
        "clinic_ru", "dentist_ru", "psychologist_ru",
        "nutritionist_ru", "personal_trainer_ru",
        # Транспорт / Логистика
        "taxi_ru", "cargo_ru", "moving_ru", "courier_ru",
        "shipping_ru", "customs_broker_ru",
        # Ивенты / Мероприятия
        "event_agency_ru", "wedding_ru", "photography_events_ru",
        "catering_ru", "decoration_ru",
        # Для бизнеса
        "outsourcing_ru", "staffing_ru", "marketing_services_ru",
        "pr_ru", "it_outsourcing_ru",
    ],

    "Здоровье": [
        # Фитнес / Спорт
        "fitness_ru", "gym_ru", "crossfit_ru", "powerlifting_ru",
        "bodybuilding_ru", "calisthenics_ru", "stretching_ru",
        "functional_training_ru", "hiit_ru", "cardio_ru",
        # Йога / Медитация
        "yoga_ru", "meditation_ru", "mindfulness_ru",
        "breathing_ru", "pranayama_ru", "qigong_ru",
        # Бег / Велоспорт
        "running_ru", "marathon_ru", "triathlon_ru",
        "cycling_ru", "swimming_ru", "skiing_ru",
        # Питание
        "nutrition_ru", "healthy_food_ru", "diet_ru",
        "keto_ru", "vegetarian_ru", "vegan_ru",
        "intermittent_fasting_ru", "detox_ru", "recipes_healthy_ru",
        # Похудение / Трансформация
        "weight_loss_ru", "body_transformation_ru",
        "slimming_ru", "pp_ru",
        # Психическое здоровье
        "mental_health_ru", "anxiety_ru", "depression_help_ru",
        "self_care_ru", "burnout_recovery_ru", "stress_ru",
        # Медицина
        "medicine_ru", "health_tips_ru", "doctor_ru",
        "pharmacology_ru", "vitamins_ru", "supplements_ru",
        "biohacking_ru", "longevity_ru", "preventive_medicine_ru",
        # Сон / Восстановление
        "sleep_ru", "recovery_ru", "hrv_ru",
        # Женское здоровье
        "womens_health_ru", "pregnancy_ru", "postpartum_ru",
        "menopause_ru", "hormones_ru",
        # Мужское здоровье
        "mens_health_ru", "testosterone_ru",
        # Детское здоровье
        "kids_health_ru", "pediatrics_ru", "vaccination_ru",
        # Альтернативная медицина
        "herbal_medicine_ru", "homeopathy_ru", "traditional_ru",
        # Спортивная медицина
        "sports_medicine_ru", "injury_prevention_ru",
        "rehabilitation_ru", "physiotherapy_ru",
    ],
}


async def seed_chats() -> None:
    total_added = 0
    total_existing = 0

    async with async_session_factory() as session:
        repo = ChatAnalyticsRepository(session)

        for topic, usernames in SEED_CHATS.items():
            print(f"\nTopic: {topic} ({len(usernames)} chats)")
            for username in usernames:
                chat, is_new = await repo.get_or_create_chat(username)
                if is_new:
                    # Установить тематику
                    chat.topic = topic
                    await session.flush()
                    total_added += 1
                    print(f"  + Added: @{username}")
                else:
                    total_existing += 1
                    print(f"  - Exists: @{username}")

        await session.commit()

    print(f"\n{'='*50}")
    print(f"Added new: {total_added}")
    print(f"Already existed: {total_existing}")
    print(f"Total in list: {total_added + total_existing}")
    print(f"\nChats ready for parsing. Run parser:")
    print("docker compose exec worker celery -A src.tasks.celery_app call \\")
    print("    tasks.parser_tasks:collect_all_chats_stats")


if __name__ == "__main__":
    asyncio.run(seed_chats())
