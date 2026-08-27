"""HTTP-слой таблицы лидеров."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_optional_user
from app.models.user import User
from app.schemas.leaderboard import LeaderboardResponse
from app.services import leaderboard as leaderboard_service
from app.services import views
from app.services.leaderboard import LeaderboardMetric

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    metric: LeaderboardMetric = LeaderboardMetric.BEST,
    limit: int = Query(default=20, ge=1, le=100),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> LeaderboardResponse:
    """
    Таблица лидеров. Доступна и без авторизации.

    Если запрос сделан с токеном, в ответе будет ещё и место самого игрока —
    даже когда он не попал в первые limit строк.
    """
    rows = await leaderboard_service.top_players(db, metric, limit)
    me = await leaderboard_service.place_of(db, metric, user) if user is not None else None

    return LeaderboardResponse(
        metric=metric,
        entries=[views.leaderboard_entry(row) for row in rows],
        me=views.leaderboard_entry(me) if me is not None else None,
    )
