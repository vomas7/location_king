"""HTTP-слой дуэлей: очередь подбора и её опрос."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, limit_by_user
from app.models.user import User
from app.schemas.duel import DuelFormatView, DuelSearchView
from app.services import duels as duels_service
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/duels", tags=["duels"])


@router.get("/format", response_model=DuelFormatView)
async def duel_format() -> DuelFormatView:
    """Условия дуэли: одни и те же для всех."""
    return DuelFormatView(
        rounds_total=duels_service.ROUNDS_TOTAL,
        view_extent_km=duels_service.VIEW_EXTENT_KM,
        difficulty=duels_service.DIFFICULTY,
        time_limit_seconds=duels_service.TIME_LIMIT_SECONDS,
    )


@router.post(
    "/queue",
    response_model=DuelSearchView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user(Limit.DUEL_QUEUE))],
)
async def enter_queue(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DuelSearchView:
    """Встать в очередь на соперника."""
    await duels_service.require_not_playing(db, user)
    state = await duels_service.enter(user)

    return DuelSearchView(searching=state.searching, code=state.code)


@router.post(
    "/queue/poll",
    response_model=DuelSearchView,
    dependencies=[Depends(limit_by_user(Limit.DUEL_POLL))],
)
async def poll_queue(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DuelSearchView:
    """
    Узнать, нашлась ли пара.

    Этот же запрос продлевает запись в очереди — перестал опрашивать, выпал, и
    счётчик ищущих остаётся честным, — и он же подбирает пару. Поэтому POST, а
    не GET: запрос меняет состояние очереди.
    """
    state = await duels_service.look(db, user)

    return DuelSearchView(searching=state.searching, code=state.code)


@router.get("/searching", response_model=DuelSearchView)
async def count_searching(user: User = Depends(get_current_user)) -> DuelSearchView:
    """
    Сколько человек ищет соперника. Ничего не меняет.

    Нужно кнопке на главном экране: решать, вставать ли в очередь, игрок
    должен до того, как встал.
    """
    return DuelSearchView(searching=await duels_service.count(), code=None)


@router.delete("/queue", status_code=status.HTTP_204_NO_CONTENT)
async def leave_queue(user: User = Depends(get_current_user)) -> None:
    """Прекратить поиск."""
    await duels_service.leave(user)
