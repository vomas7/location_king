"""Схемы друзей."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.auth import AvatarView


class FriendInviteRequest(BaseModel):
    """Заявка в друзья по коду игрока."""

    code: str = Field(min_length=1, max_length=8)


class FriendView(BaseModel):
    """
    Связь глазами того, кто смотрит.

    Чужого идентификатора здесь нет — только идентификатор самой связи: по
    нему её принимают и убирают, и больше он ни для чего не нужен.
    """

    id: int
    display_name: str
    avatar: AvatarView
    rating: int

    #: Дружба подтверждена. Иначе это заявка
    accepted: bool
    #: Заявка пришла ко мне и ждёт ответа. У подтверждённой дружбы всегда ложь
    incoming: bool

    created_at: datetime


class FriendListResponse(BaseModel):
    """Друзья игрока и его собственный код."""

    #: Его показывают тем, кого хотят добавить
    my_code: str
    friends: list[FriendView]
