"""
Handler для AI-аналитики кампаний.
Аналог Mini App AI insights.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.campaign_analytics import (
    CampaignAICB,
    get_ai_analysis_result_kb,
    get_ai_premium_lock_kb,
    get_campaign_list_kb,
)
from src.bot.keyboards.main_menu import MainMenuCB
from src.core.services.campaign_analytics_ai import campaign_analytics_ai
from src.db.models.campaign import Campaign
from src.db.models.mailing_log import MailingLog
from src.db.session import async_session_factory
from src.services import get_user_service

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(MainMenuCB.filter(F.action == "ai_campaign_analytics"))
async def show_ai_campaign_analytics(callback: CallbackQuery) -> None:
    """Показать список кампаний для AI-аналитики."""
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем тариф
        plan_str = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
        if plan_str not in ("pro", "business"):
            text = (
                "✨ <b>AI-аналитика кампаний</b>\n\n"
                "❌ Доступно только для тарифов PRO и BUSINESS\n\n"
                "AI проанализирует вашу кампанию и даст рекомендации:\n"
                "• Инсайты по результатам\n"
                "• Рекомендации по улучшению\n"
                "• Оценка эффективности (A/B/C/D)\n\n"
                "BUSINESS тариф дополнительно включает:\n"
                "• Прогноз для следующей кампании\n"
                "• Идеи для A/B тестов"
            )

            await callback.message.edit_text(
                text,
                reply_markup=get_ai_premium_lock_kb(),
            )
            return

        # Получаем завершённые кампании пользователя
        async with async_session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Campaign)
                .where(
                    Campaign.user_id == user.id,
                    Campaign.status == "done",
                )
                .order_by(Campaign.completed_at.desc())
                .limit(10)
            )
            campaigns = result.scalars().all()

        if not campaigns:
            text = (
                "✨ <b>AI-аналитика кампаний</b>\n\n"
                "У вас пока нет завершённых кампаний.\n"
                "Запустите кампанию и после завершения получите AI-анализ!"
            )

            builder = InlineKeyboardBuilder()
            builder.button(
                text="🚀 Создать кампанию",
                callback_data=MainMenuCB(action="create_campaign"),
            )
            builder.button(
                text="🔙 В меню аналитики",
                callback_data=MainMenuCB(action="analytics"),
            )
            builder.adjust(1)

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            return

        # Проверяем лимит AI-генераций
        ai_limit = 5 if plan_str == "pro" else 20
        if user.ai_generations_used >= ai_limit:
            text = (
                f"✨ <b>AI-аналитика кампаний</b>\n\n"
                f"❌ Лимит AI-генераций исчерпан\n\n"
                f"Использовано: {user.ai_generations_used} из {ai_limit}\n"
                f"Лимит обновится в начале следующего месяца."
            )

            builder = InlineKeyboardBuilder()
            builder.button(
                text="🔙 В меню аналитики",
                callback_data=MainMenuCB(action="analytics"),
            )
            builder.adjust(1)

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            return

        text = (
            "✨ <b>AI-аналитика кампаний</b>\n\n"
            f"Выберите кампанию для анализа:\n\n"
            f"💡 Лимит: {ai_limit - user.ai_generations_used} из {ai_limit} генераций"
        )

        campaigns_data = [
            {"id": c.id, "title": c.title or "Без названия", "status": c.status.value}
            for c in campaigns
        ]

        await callback.message.edit_text(
            text,
            reply_markup=get_campaign_list_kb(campaigns_data),
        )


@router.callback_query(CampaignAICB.filter(F.action == "analyze"))
async def analyze_campaign(callback: CallbackQuery, callback_data: CampaignAICB) -> None:
    """
    Выполнить AI-анализ кампании.

    callback_data.campaign_id: ID кампании для анализа.
    """
    campaign_id = int(callback_data.campaign_id)

    # Показываем индикатор загрузки
    await callback.message.edit_text(
        "✨ <b>AI-анализ кампании</b>\n\n"
        "⏳ Анализирую данные кампании...\n\n"
        "Это может занять до 30 секунд."
    )

    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        plan_str = user.plan.value if hasattr(user.plan, "value") else str(user.plan)

        # Получаем данные кампании
        async with async_session_factory() as session:
            from sqlalchemy import func, select

            campaign = await session.get(Campaign, campaign_id)

            if not campaign:
                await callback.message.edit_text("❌ Кампания не найдена")
                return

            if campaign.user_id != user.id:
                await callback.message.edit_text("❌ Это не ваша кампания")
                return

            # Получаем статистику
            logs_result = await session.execute(
                select(
                    func.count(MailingLog.id).label("total"),
                    func.count(MailingLog.id).filter(MailingLog.status == "sent").label("sent"),
                    func.count(MailingLog.id).filter(MailingLog.status == "failed").label("failed"),
                    func.min(MailingLog.sent_at).label("started_at"),
                ).where(MailingLog.campaign_id == campaign_id)
            )
            log_row = logs_result.one()

        total_sent = log_row.sent or 0
        total_failed = log_row.failed or 0
        total_logs = log_row.total or 0
        success_rate = round(total_sent / total_logs * 100, 1) if total_logs > 0 else 0.0

        campaign_data = {
            "title": campaign.title or "Без названия",
            "sent": total_sent,
            "failed": total_failed,
            "success_rate": success_rate,
            "topics": (campaign.filters_json or {}).get("topics", []),
            "date": log_row.started_at.strftime("%d.%m.%Y") if log_row.started_at else "",
        }

        # Вызываем AI
        try:
            result = await campaign_analytics_ai.generate_campaign_insights(
                campaign_data=campaign_data,
                plan=plan_str,
            )
        except Exception as e:
            logger.error(f"AI analytics error: {e}")
            await callback.message.edit_text(
                f"❌ Не удалось получить AI-анализ\n\nОшибка: {str(e)}\n\nПопробуйте позже."
            )
            return

        # Списываем генерацию
        async with async_session_factory() as session:
            from sqlalchemy import update

            await session.execute(
                update(svc._user_repo.model)
                .where(svc._user_repo.model.id == user.id)
                .values(ai_generations_used=user.ai_generations_used + 1)
            )
            await session.commit()

        # Формируем ответ
        text = "✨ <b>AI-анализ кампании</b>\n\n"
        text += f"📊 <b>{campaign.title or 'Без названия'}</b>\n\n"

        # Оценка
        grade = result.get("performance_grade", "N/A")
        grade_emoji = {"A": "🏆", "B": "✅", "C": "⚠️", "D": "❌"}.get(grade, "📊")
        text += f"{grade_emoji} <b>Оценка: {grade}</b>\n\n"

        # Инсайты
        insights = result.get("insights", [])
        if insights:
            text += "<b>💡 Инсайты:</b>\n"
            for i, insight in enumerate(insights, 1):
                text += f"{i}. {insight}\n"
            text += "\n"

        # Рекомендации
        recommendations = result.get("recommendations", [])
        if recommendations:
            text += "<b>📋 Рекомендации:</b>\n"
            for i, rec in enumerate(recommendations, 1):
                text += f"{i}. {rec}\n"
            text += "\n"

        # Прогноз (BUSINESS)
        forecast = result.get("forecast")
        if forecast:
            text += f"<b>🔮 Прогноз:</b>\n{forecast}\n\n"

        # A/B тест (BUSINESS)
        ab_test = result.get("ab_test_suggestion")
        if ab_test:
            text += f"<b>💡 A/B тест:</b>\n{ab_test}\n\n"

        # Лимит
        ai_limit = 5 if plan_str == "pro" else 20
        text += f"\n💡 Осталось генераций: {ai_limit - user.ai_generations_used - 1} из {ai_limit}"

        await callback.message.edit_text(
            text,
            reply_markup=get_ai_analysis_result_kb(campaign_id),
        )


@router.callback_query(CampaignAICB.filter(F.action == "list"))
async def show_campaign_list(callback: CallbackQuery) -> None:
    """Показать список кампаний заново."""
    await show_ai_campaign_analytics(callback)
