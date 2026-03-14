"""
Reputation Service — сервис для управления репутацией пользователей.
Система доверия и модерации (НЕ геймификация!).

Важно: XP ≠ Репутация
- XP (User.advertiser_xp) — геймификация, уровни, достижения
- ReputationScore — доверие, штрафы, блокировки
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.reputation_history import ReputationAction
from src.db.repositories.reputation_repo import ReputationRepo

logger = logging.getLogger(__name__)


class ReputationService:
    """
    Сервис для управления репутацией пользователей.

    Константы штрафов/бонусов:
        DELTA_PUBLICATION = +1.0
        DELTA_REVIEW_5STAR = +2.0
        DELTA_REVIEW_4STAR = +1.0
        DELTA_REVIEW_3STAR = 0.0
        DELTA_REVIEW_2STAR = -1.0
        DELTA_REVIEW_1STAR = -2.0
        DELTA_CANCEL_BEFORE = -5.0
        DELTA_CANCEL_AFTER = -20.0
        DELTA_CANCEL_SYSTEMATIC = -20.0
        DELTA_REJECT_INVALID_1 = -10.0
        DELTA_REJECT_INVALID_2 = -15.0
        DELTA_REJECT_INVALID_3 = -20.0
        DELTA_REJECT_FREQUENT = -5.0
        DELTA_RECOVERY_30DAYS = +5.0
        SCORE_MIN = 0.0
        SCORE_MAX = 10.0
        SCORE_AFTER_BAN = 2.0
        BAN_DURATION_DAYS = 7
        PERMANENT_BAN_VIOLATIONS = 5
    """

    # Константы штрафов/бонусов
    DELTA_PUBLICATION = +1.0
    DELTA_REVIEW_5STAR = +2.0
    DELTA_REVIEW_4STAR = +1.0
    DELTA_REVIEW_3STAR = 0.0
    DELTA_REVIEW_2STAR = -1.0
    DELTA_REVIEW_1STAR = -2.0
    DELTA_CANCEL_BEFORE = -5.0
    DELTA_CANCEL_AFTER = -20.0
    DELTA_CANCEL_SYSTEMATIC = -20.0
    DELTA_REJECT_INVALID_1 = -10.0
    DELTA_REJECT_INVALID_2 = -15.0
    DELTA_REJECT_INVALID_3 = -20.0
    DELTA_REJECT_FREQUENT = -5.0
    DELTA_RECOVERY_30DAYS = +5.0
    SCORE_MIN = 0.0
    SCORE_MAX = 10.0
    SCORE_AFTER_BAN = 2.0
    BAN_DURATION_DAYS = 7
    PERMANENT_BAN_VIOLATIONS = 5

    def __init__(
        self,
        session: AsyncSession,
        reputation_repo: ReputationRepo,
    ):
        """
        Инициализация сервиса.

        Args:
            session: Асинхронная сессия SQLAlchemy.
            reputation_repo: Репозиторий репутации.
        """
        self.session = session
        self.reputation_repo = reputation_repo

    async def on_publication(
        self,
        advertiser_id: int,
        owner_id: int,
        placement_request_id: int,
    ) -> None:
        """
        Успешная публикация: +1 advertiser, +1 owner.

        Args:
            advertiser_id: ID рекламодателя.
            owner_id: ID владельца.
            placement_request_id: ID заявки.
        """
        # Advertiser +1
        await self._apply_delta(
            user_id=advertiser_id,
            role="advertiser",
            delta=self.DELTA_PUBLICATION,
            action=ReputationAction.PUBLICATION,
            placement_request_id=placement_request_id,
        )

        # Owner +1
        await self._apply_delta(
            user_id=owner_id,
            role="owner",
            delta=self.DELTA_PUBLICATION,
            action=ReputationAction.PUBLICATION,
            placement_request_id=placement_request_id,
        )

    async def on_review(
        self,
        reviewer_id: int,
        reviewed_id: int,
        reviewer_role: str,  # "advertiser" (рецензирует owner) или "owner" (рецензирует advertiser)
        stars: int,  # 1-5
        placement_request_id: int,
    ) -> None:
        """
        Начислить дельту за отзыв reviewed_id по шкале звёзд.
        reviewer_role определяет роль reviewed_id (обратная).

        Args:
            reviewer_id: ID оставившего отзыв.
            reviewed_id: ID получившего отзыв.
            reviewer_role: Роль оставившего отзыв ("advertiser" или "owner").
            stars: Количество звёзд (1-5).
            placement_request_id: ID заявки.
        """
        # Определяем дельту по звёздам
        delta_map = {
            5: self.DELTA_REVIEW_5STAR,
            4: self.DELTA_REVIEW_4STAR,
            3: self.DELTA_REVIEW_3STAR,
            2: self.DELTA_REVIEW_2STAR,
            1: self.DELTA_REVIEW_1STAR,
        }

        delta = delta_map.get(stars, 0.0)

        # Определяем действие
        action_map = {
            5: ReputationAction.REVIEW_5STAR,
            4: ReputationAction.REVIEW_4STAR,
            3: ReputationAction.REVIEW_3STAR,
            2: ReputationAction.REVIEW_2STAR,
            1: ReputationAction.REVIEW_1STAR,
        }

        action = action_map.get(stars, ReputationAction.REVIEW_3STAR)

        # reviewed_id получает дельту, роль обратная reviewer_role
        reviewed_role = "owner" if reviewer_role == "advertiser" else "advertiser"

        await self._apply_delta(
            user_id=reviewed_id,
            role=reviewed_role,
            delta=delta,
            action=action,
            placement_request_id=placement_request_id,
            comment=f"Review {stars} stars",
        )

    async def on_advertiser_cancel(
        self,
        advertiser_id: int,
        placement_request_id: int,
        after_confirmation: bool,
    ) -> None:
        """
        Штраф за отмену.
        after_confirmation=True → -20 (CANCEL_AFTER)
        after_confirmation=False → -5 (CANCEL_BEFORE)

        После штрафа: проверить count_cancellations_in_30_days.
        Если >= 3 → ещё DELTA_CANCEL_SYSTEMATIC.

        Args:
            advertiser_id: ID рекламодателя.
            placement_request_id: ID заявки.
            after_confirmation: После подтверждения владельцем.
        """
        delta = self.DELTA_CANCEL_AFTER if after_confirmation else self.DELTA_CANCEL_BEFORE
        action = (
            ReputationAction.CANCEL_AFTER if after_confirmation else ReputationAction.CANCEL_BEFORE
        )

        await self._apply_delta(
            user_id=advertiser_id,
            role="advertiser",
            delta=delta,
            action=action,
            placement_request_id=placement_request_id,
        )

        # Проверка на систематические отмены
        from src.db.repositories.placement_request_repo import PlacementRequestRepo

        placement_repo = PlacementRequestRepo(self.session)
        cancellations = await placement_repo.count_cancellations_in_30_days(advertiser_id)

        if cancellations >= 3:
            await self._apply_delta(
                user_id=advertiser_id,
                role="advertiser",
                delta=self.DELTA_CANCEL_SYSTEMATIC,
                action=ReputationAction.CANCEL_SYSTEMATIC,
                placement_request_id=placement_request_id,
                comment="Systematic cancellations (3+ in 30 days)",
            )

    async def on_invalid_rejection(
        self,
        owner_id: int,
        placement_request_id: int,
    ) -> None:
        """
        Штраф за невалидный отказ.
        Получить streak из count_invalid_rejections_streak.
        streak=1 → -10, streak=2 → -15, streak>=3 → -20 + бан 7 дней.
        При бане: set_block(owner_id, 'owner', now()+7days).

        Args:
            owner_id: ID владельца.
            placement_request_id: ID заявки.
        """
        streak = await self.reputation_repo.count_invalid_rejections_streak(owner_id)

        if streak == 0:
            delta = self.DELTA_REJECT_INVALID_1
            action = ReputationAction.REJECT_INVALID_1
        elif streak == 1:
            delta = self.DELTA_REJECT_INVALID_2
            action = ReputationAction.REJECT_INVALID_2
        else:  # streak >= 2
            delta = self.DELTA_REJECT_INVALID_3
            action = ReputationAction.REJECT_INVALID_3

        await self._apply_delta(
            user_id=owner_id,
            role="owner",
            delta=delta,
            action=action,
            placement_request_id=placement_request_id,
        )

        # Бан при streak >= 2 (третий невалидный отказ)
        if streak >= 2:
            blocked_until = datetime.now(UTC) + timedelta(days=self.BAN_DURATION_DAYS)
            await self.reputation_repo.set_block(
                user_id=owner_id,
                role="owner",
                blocked_until=blocked_until,
                reason="3 invalid rejections in a row",
            )

    async def on_frequent_rejections(self, owner_id: int) -> None:
        """
        Штраф -5 за частые отказы (>50% заявок).

        Args:
            owner_id: ID владельца.
        """
        await self._apply_delta(
            user_id=owner_id,
            role="owner",
            delta=self.DELTA_REJECT_FREQUENT,
            action=ReputationAction.REJECT_FREQUENT,
            comment="Frequent rejections (>50%)",
        )

    async def on_30days_clean(self, user_id: int, role: str) -> None:
        """
        +5 за 30 дней без нарушений.
        Вызывается Celery-задачей раз в день.

        Args:
            user_id: ID пользователя.
            role: Роль ("advertiser" или "owner").
        """
        await self._apply_delta(
            user_id=user_id,
            role=role,
            delta=self.DELTA_RECOVERY_30DAYS,
            action=ReputationAction.RECOVERY_30DAYS,
            comment="30 days without violations",
        )

    async def check_and_unblock(self, user_id: int) -> bool:
        """
        Проверить истёк ли срок блокировки.
        Если да: снять блокировку, сбросить score до 2.0, записать BAN_RESET.
        Вернуть True если разблокирован.

        Args:
            user_id: ID пользователя.

        Returns:
            True если разблокирован.
        """
        score = await self.reputation_repo.get_by_user(user_id)
        if not score:
            return False

        unblocked = False

        # Проверка advertiser блокировки
        if (
            score.is_advertiser_blocked
            and score.advertiser_blocked_until
            and score.advertiser_blocked_until < datetime.now(UTC)
        ):
            await self.reputation_repo.set_block(
                user_id=user_id,
                role="advertiser",
                blocked_until=None,
            )
            # Сброс score до 2.0
            await self._apply_delta(
                user_id=user_id,
                role="advertiser",
                delta=self.SCORE_AFTER_BAN - score.advertiser_score,
                action=ReputationAction.BAN_RESET,
                comment="Score reset after ban expiration",
            )
            unblocked = True

        # Проверка owner блокировки
        if (
            score.is_owner_blocked
            and score.owner_blocked_until
            and score.owner_blocked_until < datetime.now(UTC)
        ):
            await self.reputation_repo.set_block(
                user_id=user_id,
                role="owner",
                blocked_until=None,
            )
            # Сброс score до 2.0
            await self._apply_delta(
                user_id=user_id,
                role="owner",
                delta=self.SCORE_AFTER_BAN - score.owner_score,
                action=ReputationAction.BAN_RESET,
                comment="Score reset after ban expiration",
            )
            unblocked = True

        return unblocked

    async def is_blocked(self, user_id: int, role: str) -> bool:
        """
        Проверить заблокирован ли пользователь в роли role.

        Args:
            user_id: ID пользователя.
            role: Роль ("advertiser" или "owner").

        Returns:
            True если заблокирован.
        """
        score = await self.reputation_repo.get_by_user(user_id)
        if not score:
            return False

        if (
            role == "advertiser"
            and score.is_advertiser_blocked
            and (
                not score.advertiser_blocked_until
                or score.advertiser_blocked_until > datetime.now(UTC)
            )
        ):
            return True

        return (
            role == "owner"
            and score.is_owner_blocked
            and (not score.owner_blocked_until or score.owner_blocked_until > datetime.now(UTC))
        )

    async def get_score(self, user_id: int, role: str) -> float:
        """
        Получить текущий score. 5.0 если записи нет.

        Args:
            user_id: ID пользователя.
            role: Роль ("advertiser" или "owner").

        Returns:
            Текущий score.
        """
        score = await self.reputation_repo.get_or_create(user_id)

        if role == "advertiser":
            return score.advertiser_score
        elif role == "owner":
            return score.owner_score

        return 5.0

    async def _apply_delta(
        self,
        user_id: int,
        role: str,
        delta: float,
        action: ReputationAction,
        placement_request_id: int | None = None,
        comment: str | None = None,
    ) -> float:
        """
        Приватный метод. Применить дельту к score.
        Зажать в [SCORE_MIN, SCORE_MAX].
        Записать в историю через reputation_repo.add_history().
        После применения: проверить violations >= PERMANENT_BAN_VIOLATIONS → перманентная блокировка.

        Args:
            user_id: ID пользователя.
            role: Роль ("advertiser" или "owner").
            delta: Изменение score.
            action: Тип события.
            placement_request_id: ID заявки.
            comment: Комментарий.

        Returns:
            Новый score.
        """
        # Получаем или создаём репутацию
        score = await self.reputation_repo.get_or_create(user_id)

        # Получаем текущий score
        current_score = (
            score.advertiser_score if role == "advertiser" else score.owner_score
        )

        # Применяем дельту
        new_score = current_score + delta

        # Зажимаем в [SCORE_MIN, SCORE_MAX]
        new_score = max(self.SCORE_MIN, min(self.SCORE_MAX, new_score))

        # Обновляем score
        await self.reputation_repo.update_score(
            user_id=user_id,
            role=role,
            delta=delta,
            new_score=new_score,
        )

        # Записываем в историю
        await self.reputation_repo.add_history(
            user_id=user_id,
            action=action,
            delta=delta,
            new_score=new_score,
            role=role,
            placement_request_id=placement_request_id,
            comment=comment,
        )

        # Инкремент нарушений если delta < 0
        if delta < 0:
            await self.reputation_repo.increment_violations(user_id=user_id, role=role)

            # Проверка на перманентную блокировку
            score = await self.reputation_repo.get_by_user(user_id)
            if score:
                violations = (
                    score.advertiser_violations if role == "advertiser" else score.owner_violations
                )
                if violations >= self.PERMANENT_BAN_VIOLATIONS:
                    # Перманентная блокировка
                    await self.reputation_repo.set_block(
                        user_id=user_id,
                        role=role,
                        blocked_until=None,  # None = перманентно
                        reason=f"Permanent ban: {violations} violations",
                    )

        return new_score
