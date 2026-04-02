"""Tests for ReviewService."""

import asyncio
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import settings
from src.core.services.review_service import ReviewService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.review import Review
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User

# ---------------------------------------------------------------------------
# Override event_loop at function scope to avoid conflict with conftest's
# session-scoped event_loop + asyncio_default_fixture_loop_scope=function
# ---------------------------------------------------------------------------


@pytest.fixture
def event_loop():
    """Function-scoped event loop, shadows conftest's session-scoped one."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# Self-contained session fixture (tables already exist via migrations)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Function-scoped session with rollback after each test.

    Connects directly to the running application DB. Tables already exist.
    No create_all/drop_all — avoids CircularDependencyError on teardown.
    """
    engine = create_async_engine(str(settings.database_url), echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def advertiser(db_session: AsyncSession) -> User:
    user = User(
        telegram_id=900111001,
        username="test_advertiser_rv",
        first_name="Advertiser",
        current_role="advertiser",
        credits=1000,
        referral_code="rv_adv_001",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def owner(db_session: AsyncSession) -> User:
    user = User(
        telegram_id=900111002,
        username="test_owner_rv",
        first_name="Owner",
        current_role="owner",
        credits=500,
        referral_code="rv_own_001",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def channel(db_session: AsyncSession, owner: User) -> TelegramChat:
    chat = TelegramChat(
        telegram_id=-1009000000001,
        username="rv_test_channel",
        title="Review Test Channel",
        owner_id=owner.id,
        member_count=10000,
        is_active=True,
    )
    db_session.add(chat)
    await db_session.flush()
    await db_session.refresh(chat)
    return chat


@pytest_asyncio.fixture
async def published_placement(
    db_session: AsyncSession,
    advertiser: User,
    owner: User,
    channel: TelegramChat,
) -> PlacementRequest:
    req = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        status=PlacementStatus.published,
        ad_text="Тестовый рекламный текст для отзыва",
        proposed_price=Decimal("1000.00"),
        final_price=Decimal("1000.00"),
    )
    db_session.add(req)
    await db_session.flush()
    await db_session.refresh(req)
    return req


@pytest.fixture
def review_service() -> ReviewService:
    return ReviewService()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateReview:
    @pytest.mark.asyncio
    async def test_create_review_success(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        published_placement: PlacementRequest,
        advertiser: User,
        owner: User,
    ) -> None:
        """Успешное создание отзыва."""
        review = await review_service.create_review(
            placement_request_id=published_placement.id,
            reviewer_id=advertiser.id,
            reviewed_id=owner.id,
            rating=5,
            comment="Отличное размещение!",
            session=db_session,
        )

        assert isinstance(review, Review)
        assert review.id is not None
        assert review.placement_request_id == published_placement.id
        assert review.reviewer_id == advertiser.id
        assert review.reviewed_id == owner.id
        assert review.rating == 5
        assert review.comment == "Отличное размещение!"

    @pytest.mark.asyncio
    async def test_create_review_invalid_rating_raises(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        published_placement: PlacementRequest,
        advertiser: User,
        owner: User,
    ) -> None:
        """Рейтинг вне диапазона 1-5 — ValueError."""
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            await review_service.create_review(
                placement_request_id=published_placement.id,
                reviewer_id=advertiser.id,
                reviewed_id=owner.id,
                rating=6,
                comment=None,
                session=db_session,
            )

    @pytest.mark.asyncio
    async def test_create_review_duplicate_raises(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        published_placement: PlacementRequest,
        advertiser: User,
        owner: User,
    ) -> None:
        """Повторный отзыв от того же reviewer_id на тот же placement — ValueError."""
        await review_service.create_review(
            placement_request_id=published_placement.id,
            reviewer_id=advertiser.id,
            reviewed_id=owner.id,
            rating=4,
            comment="Первый отзыв",
            session=db_session,
        )

        with pytest.raises(ValueError, match="Review already exists"):
            await review_service.create_review(
                placement_request_id=published_placement.id,
                reviewer_id=advertiser.id,
                reviewed_id=owner.id,
                rating=3,
                comment="Дубль",
                session=db_session,
            )

    @pytest.mark.asyncio
    async def test_create_review_both_sides(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        published_placement: PlacementRequest,
        advertiser: User,
        owner: User,
    ) -> None:
        """Advertiser и owner могут оба оставить отзыв на одно размещение."""
        review_adv = await review_service.create_review(
            placement_request_id=published_placement.id,
            reviewer_id=advertiser.id,
            reviewed_id=owner.id,
            rating=5,
            comment="От рекламодателя",
            session=db_session,
        )
        review_own = await review_service.create_review(
            placement_request_id=published_placement.id,
            reviewer_id=owner.id,
            reviewed_id=advertiser.id,
            rating=4,
            comment="От владельца",
            session=db_session,
        )

        assert review_adv.id != review_own.id
        assert review_adv.reviewer_id == advertiser.id
        assert review_own.reviewer_id == owner.id

    @pytest.mark.asyncio
    async def test_create_review_not_published_raises(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        advertiser: User,
        owner: User,
        channel: TelegramChat,
    ) -> None:
        """Нельзя оставить отзыв на размещение не в статусе published."""
        req = PlacementRequest(
            advertiser_id=advertiser.id,
            owner_id=owner.id,
            channel_id=channel.id,
            status=PlacementStatus.escrow,
            ad_text="Ещё не опубликовано",
            proposed_price=Decimal("500.00"),
        )
        db_session.add(req)
        await db_session.flush()

        with pytest.raises(ValueError, match="Can only review published placements"):
            await review_service.create_review(
                placement_request_id=req.id,
                reviewer_id=advertiser.id,
                reviewed_id=owner.id,
                rating=3,
                comment=None,
                session=db_session,
            )


class TestRecalculateChannelRating:
    @pytest.mark.asyncio
    async def test_recalculate_returns_float_in_range(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        advertiser: User,
        owner: User,
        channel: TelegramChat,
    ) -> None:
        """После создания отзывов рейтинг канала — float в диапазоне 0.0–5.0."""
        for rating in (5, 4, 3):
            req = PlacementRequest(
                advertiser_id=advertiser.id,
                owner_id=owner.id,
                channel_id=channel.id,
                status=PlacementStatus.published,
                ad_text=f"Объявление для рейтинга {rating}",
                proposed_price=Decimal("1000.00"),
                final_price=Decimal("1000.00"),
            )
            db_session.add(req)
            await db_session.flush()
            rev = Review(
                placement_request_id=req.id,
                reviewer_id=advertiser.id,
                reviewed_id=owner.id,
                rating=rating,
                comment=None,
            )
            db_session.add(rev)
            await db_session.flush()

        result = await review_service.recalculate_channel_rating(channel.id, db_session)

        assert isinstance(result, float)
        assert 0.0 <= result <= 5.0

    @pytest.mark.asyncio
    async def test_recalculate_unknown_channel_returns_zero(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
    ) -> None:
        """Несуществующий channel_id → 0.0."""
        result = await review_service.recalculate_channel_rating(999999, db_session)
        assert result == 0.0


class TestGetChannelReviews:
    @pytest.mark.asyncio
    async def test_get_channel_reviews_returns_list(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        published_placement: PlacementRequest,
        advertiser: User,
        owner: User,
        channel: TelegramChat,
    ) -> None:
        """get_channel_reviews возвращает список отзывов для канала."""
        review = Review(
            placement_request_id=published_placement.id,
            reviewer_id=advertiser.id,
            reviewed_id=owner.id,
            rating=5,
            comment="Хороший канал",
        )
        db_session.add(review)
        await db_session.flush()

        reviews = await review_service.get_channel_reviews(channel.id, db_session)

        assert isinstance(reviews, list)
        assert len(reviews) >= 1
        assert all(isinstance(r, Review) for r in reviews)


class TestGetUserRating:
    @pytest.mark.asyncio
    async def test_get_user_rating_returns_float(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        published_placement: PlacementRequest,
        advertiser: User,
        owner: User,
    ) -> None:
        """get_user_rating возвращает float после появления отзывов."""
        review = Review(
            placement_request_id=published_placement.id,
            reviewer_id=advertiser.id,
            reviewed_id=owner.id,
            rating=4,
            comment=None,
        )
        db_session.add(review)
        await db_session.flush()

        rating = await review_service.get_user_rating(owner.id, "owner", db_session)

        assert isinstance(rating, float)
        assert rating == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_get_user_rating_no_reviews_returns_zero(
        self,
        db_session: AsyncSession,
        review_service: ReviewService,
        owner: User,
    ) -> None:
        """Пользователь без отзывов → 0.0."""
        rating = await review_service.get_user_rating(owner.id, "owner", db_session)
        assert rating == 0.0
