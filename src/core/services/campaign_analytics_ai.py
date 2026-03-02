"""
AI-аналитика кампаний через OpenRouter.
Доступна только для тарифов PRO и BUSINESS.

Использует существующий ai_service.py.
"""
import json
import logging
import re
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
        from src.core.services.ai_service import AIService

        ai = AIService()

        prompt = self._build_prompt(campaign_data, plan)

        try:
            response = await ai.generate(
                prompt=prompt,
                user_plan=plan,
                use_cache=False,
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
