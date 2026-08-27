"""Схемы комнат мультиплеера."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.game import SessionSummary


class MatchStanding(BaseModel):
    """Строка таблицы комнаты."""

    rank: int
    display_name: str
    total_score: int
    rounds_done: int
    is_finished: bool
    #: Чтобы клиент подсветил строку игрока, не зная чужих идентификаторов
    is_you: bool
    finished_at: datetime | None


class MatchView(BaseModel):
    """Комната глазами участника."""

    code: str
    status: str
    host_name: str
    is_host: bool
    rounds_total: int
    time_limit_seconds: int | None
    players: int
    created_at: datetime

    #: Партия игрока в этой комнате, если он уже входил
    my_session: SessionSummary | None
    standings: list[MatchStanding]


class MatchSummary(BaseModel):
    """Комната в списке созданных игроком."""

    code: str
    status: str
    rounds_total: int
    players: int
    created_at: datetime


class MatchListResponse(BaseModel):
    """Последние комнаты игрока."""

    matches: list[MatchSummary]
