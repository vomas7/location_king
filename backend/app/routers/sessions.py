"""HTTP-слой игровых сессий."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, limit_by_user
from app.models.game_session import GameSession
from app.models.user import User
from app.schemas.game import (
    SessionHistoryResponse,
    SessionStateResponse,
    StartSessionRequest,
)
from app.services import game as game_service
from app.services import views
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionStateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user(Limit.START_SESSION))],
)
async def start_session(
    payload: StartSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    """Начать партию и получить первый раунд."""
    session, first_round = await game_service.start_session(
        db,
        user,
        rounds_total=payload.rounds_total,
        view_extent_km=payload.view_extent_km,
        difficulty=payload.difficulty,
        category=payload.category,
        continent=payload.continent,
        zone_id=payload.zone_id,
        time_limit_seconds=payload.time_limit_seconds,
    )

    return SessionStateResponse(
        session=views.session_view(session),
        current_round=views.round_view(first_round),
        results=[],
    )


@router.get("", response_model=SessionHistoryResponse)
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionHistoryResponse:
    """История партий игрока, новые сверху."""
    sessions, total = await game_service.list_sessions(db, user, limit, offset)

    return SessionHistoryResponse(
        sessions=[views.session_summary(session) for session in sessions],
        total=total,
    )


# Объявлено до /{session_id}: иначе «current» попал бы в него как идентификатор
@router.get("/current", response_model=SessionStateResponse | None)
async def get_current_session(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse | None:
    """
    Незавершённая партия, чтобы продолжить её после перезагрузки страницы.

    Если её нет — это не ошибка, а обычное состояние нового игрока, поэтому
    ответ 200 с null, а не 404.
    """
    session = await game_service.current_session(db, user)
    if session is None:
        return None

    return await _session_state(db, session)


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    """Текущее состояние партии: активный раунд и история завершённых."""
    session = await game_service.get_session_for_user(db, user, session_id)
    return await _session_state(db, session)


async def _session_state(db: AsyncSession, session: GameSession) -> SessionStateResponse:
    """Состояние партии: активный раунд и история завершённых."""
    current = await game_service.active_round(db, session)

    return SessionStateResponse(
        session=views.session_view(session),
        current_round=views.round_view(current) if current is not None else None,
        results=await views.session_results(db, session.rounds),
    )


@router.post("/{session_id}/finish", response_model=SessionStateResponse)
async def finish_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    """Завершить партию досрочно."""
    session = await game_service.get_session_for_user(db, user, session_id)
    await game_service.finish_session(db, session)

    return SessionStateResponse(
        session=views.session_view(session),
        current_round=None,
        results=await views.session_results(db, session.rounds),
    )
