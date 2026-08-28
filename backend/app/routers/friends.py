"""HTTP-слой друзей."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, limit_by_user
from app.models.user import User
from app.schemas.friend import FriendInviteRequest, FriendListResponse, FriendView
from app.services import friends as friends_service
from app.services import views
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.get("", response_model=FriendListResponse)
async def list_friends(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendListResponse:
    """Друзья, заявки в обе стороны и собственный код игрока."""
    connections = await friends_service.connections(db, user)

    return FriendListResponse(
        my_code=user.friend_code,
        friends=[views.friend_view(item) for item in connections],
    )


@router.post(
    "",
    response_model=FriendView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user(Limit.FRIEND_INVITE))],
)
async def invite_friend(
    payload: FriendInviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendView:
    """Позвать в друзья по коду игрока."""
    return views.friend_view(await friends_service.invite(db, user, payload.code))


@router.post(
    "/{friendship_id}/accept",
    response_model=FriendView,
    dependencies=[Depends(limit_by_user(Limit.FRIEND_MANAGE))],
)
async def accept_friend(
    friendship_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FriendView:
    """Принять заявку."""
    return views.friend_view(await friends_service.accept(db, user, friendship_id))


@router.delete(
    "/{friendship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(limit_by_user(Limit.FRIEND_MANAGE))],
)
async def remove_friend(
    friendship_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Отклонить заявку, отозвать свою или расстаться."""
    await friends_service.remove(db, user, friendship_id)
