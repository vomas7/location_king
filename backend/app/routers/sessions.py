"""HTTP-слой игровых сессий."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.game import SessionStateResponse, StartSessionRequest
from app.services import game as game_service
from app.services import views

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionStateResponse, status_code=status.HTTP_201_CREATED)
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
        zone_id=payload.zone_id,
    )

    return SessionStateResponse(
        session=views.session_view(session),
        current_round=views.round_view(first_round, index=1),
        results=[],
    )


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    """Текущее состояние партии: активный раунд и история завершённых."""
    session = await game_service.get_session_for_user(db, user, session_id)
    current = await game_service.active_round(db, session)

    return SessionStateResponse(
        session=views.session_view(session),
        current_round=(
            views.round_view(current, views.round_index(session, current))
            if current is not None
            else None
        ),
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
