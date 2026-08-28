"""HTTP-слой комнат мультиплеера."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, limit_by_user
from app.models.match import Match
from app.models.user import User
from app.schemas.game import RoundsRequest, SessionStateResponse
from app.schemas.match import MatchListResponse, MatchView
from app.services import game as game_service
from app.services import matches as matches_service
from app.services import views
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.post(
    "",
    response_model=MatchView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user(Limit.START_SESSION))],
)
async def create_match(
    payload: RoundsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchView:
    """Создать комнату и получить её код."""
    match = await matches_service.create(
        db,
        user,
        rounds_total=payload.rounds_total,
        view_extent_km=payload.view_extent_km,
        category=payload.category,
        continent=payload.continent,
        country_group=payload.country_group,
        difficulty=payload.difficulty,
        time_limit_seconds=payload.time_limit_seconds,
    )
    return await _match_view(db, match, user)


# Объявлено до /{code}: иначе «mine» попало бы в него как код комнаты
@router.get("/mine", response_model=MatchListResponse)
async def list_my_matches(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchListResponse:
    """Последние комнаты, созданные игроком."""
    matches = await matches_service.hosted_recently(db, user)
    players = await matches_service.player_counts(db, [match.code for match in matches])

    return MatchListResponse(
        matches=[views.match_summary(match, players.get(match.code, 0)) for match in matches],
    )


@router.get("/{code}", response_model=MatchView)
async def get_match(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchView:
    """Состояние комнаты и таблица результатов."""
    match = await matches_service.get(db, code)
    return await _match_view(db, match, user)


@router.post(
    "/{code}/join",
    response_model=SessionStateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user(Limit.START_SESSION))],
)
async def join_match(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    """Войти в комнату и получить первый раунд её серии."""
    match = await matches_service.get(db, code)
    session, first_round = await game_service.start_match(db, user, match)

    return SessionStateResponse(
        session=views.session_view(session),
        current_round=await views.round_view(db, first_round),
        results=[],
    )


@router.post("/{code}/close", response_model=MatchView)
async def close_match(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchView:
    """Закрыть набор в комнату. Может только хост."""
    match = await matches_service.get(db, code)
    await matches_service.close(db, match, user)

    return await _match_view(db, match, user)


async def _match_view(db: AsyncSession, match: Match, user: User) -> MatchView:
    """Комната вместе с таблицей: партия игрока берётся из той же выборки."""
    sessions = await matches_service.standings(db, match)
    mine = next((item for item in sessions if item.user_id == user.id), None)

    return views.match_view(match, sessions, user, mine)
