"""Схемы челленджа дня."""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.auth import AvatarView
from app.schemas.game import SessionSummary


class DailyResult(BaseModel):
    """Строка таблицы дня."""

    rank: int
    display_name: str
    avatar: AvatarView
    total_score: int
    finished_at: datetime | None


class DailyChallengeView(BaseModel):
    """Состояние челленджа дня для текущего игрока."""

    day: date
    rounds_total: int
    view_extent_km: float

    #: Партия игрока по этому челленджу, если он его уже начинал
    my_session: SessionSummary | None
    #: Сколько игроков уже дошли до конца
    finished_players: int

    #: Сколько дней подряд игрок доходит до конца челленджа
    current_streak: int
    #: Самая длинная его серия за всё время
    best_streak: int

    results: list[DailyResult]
