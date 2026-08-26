"""HTTP-слой раундов и прокси спутниковых тайлов."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.game import GuessRequest, GuessResponse, RoundView
from app.services import game as game_service
from app.services import tiles as tiles_service
from app.services import views

router = APIRouter(prefix="/api/rounds", tags=["rounds"])


@router.get("/{round_id}", response_model=RoundView)
async def get_round(
    round_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoundView:
    """Активный раунд. Координат цели в ответе нет."""
    round_obj = await game_service.get_round_for_user(db, user, round_id)
    session = await game_service.get_session_for_user(db, user, round_obj.session_id)

    return views.round_view(round_obj, views.round_index(session, round_obj))


@router.post("/{round_id}/guess", response_model=GuessResponse)
async def submit_guess(
    round_id: int,
    payload: GuessRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuessResponse:
    """Принять догадку и показать, где была цель."""
    round_obj = await game_service.get_round_for_user(db, user, round_id)

    finished_round, next_round = await game_service.submit_guess(
        db,
        user,
        round_obj,
        longitude=payload.longitude,
        latitude=payload.latitude,
    )

    session = await game_service.get_session_for_user(db, user, round_obj.session_id)
    index = views.round_index(session, finished_round)

    return GuessResponse(
        result=await views.round_result(db, finished_round, index),
        session=views.session_view(session),
        next_round=(views.round_view(next_round, index + 1) if next_round is not None else None),
        is_session_finished=not session.is_active,
    )


@router.get(
    "/{round_id}/tiles/{z}/{x}/{y}.jpg",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def get_tile(
    round_id: int,
    z: int,
    x: int,
    y: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Тайл снимка по локальным координатам раунда.

    Глобальные координаты остаются на сервере, выход за пределы области — 404.
    """
    round_obj = await game_service.get_round_for_user(db, user, round_id)
    tile = await tiles_service.get_tile(round_obj, z, x, y)

    return Response(
        content=tile,
        media_type=tiles_service.TILE_CONTENT_TYPE,
        headers={"Cache-Control": f"private, max-age={settings.tile_cache_ttl_seconds}"},
    )
