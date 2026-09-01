"""HTTP-слой счётчика игроков."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.community import CommunityView
from app.services import community as community_service

router = APIRouter(prefix="/api/community", tags=["community"])


@router.get("", response_model=CommunityView)
async def community(db: AsyncSession = Depends(get_db)) -> CommunityView:
    """
    Сколько людей играет. Единственный публичный запрос без авторизации:
    первый экран показывает это число ещё до того, как игрок вошёл.
    """
    return CommunityView(players=await community_service.players(db))
