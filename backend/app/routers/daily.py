"""HTTP-слой челленджа дня."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, limit_by_user
from app.models.user import User
from app.schemas.daily import DailyChallengeView
from app.schemas.game import SessionStateResponse
from app.services import daily as daily_service
from app.services import game as game_service
from app.services import views
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/challenge", tags=["challenge"])


@router.get("/today", response_model=DailyChallengeView)
async def get_today(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DailyChallengeView:
    """Условия челленджа дня, результат игрока и таблица дня."""
    day = daily_service.today()
    current_streak, best_streak = await daily_service.streak(db, user, day)

    return DailyChallengeView(
        day=day,
        rounds_total=daily_service.ROUNDS_TOTAL,
        view_extent_km=daily_service.VIEW_EXTENT_KM,
        my_session=views.session_summary_or_none(await daily_service.played_session(db, user, day)),
        finished_players=await daily_service.played_count(db, day),
        current_streak=current_streak,
        best_streak=best_streak,
        results=[
            views.daily_result(rank, session)
            for rank, session in enumerate(await daily_service.results(db, day), start=1)
        ],
    )


@router.post(
    "/today/start",
    response_model=SessionStateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user(Limit.START_SESSION))],
)
async def start_today(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    """Начать челлендж дня. Второй раз за день — 409."""
    session, first_round = await game_service.start_daily_challenge(db, user, daily_service.today())

    return SessionStateResponse(
        session=views.session_view(session),
        current_round=views.round_view(first_round),
        results=[],
    )
