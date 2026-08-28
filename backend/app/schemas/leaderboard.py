"""Схемы таблицы лидеров."""

from pydantic import BaseModel

from app.models.enums import Continent, CountryGroup, Difficulty
from app.schemas.auth import AvatarView
from app.services.leaderboard import LeaderboardMetric


class LeaderboardEntry(BaseModel):
    """Игрок и его место."""

    rank: int
    user_id: int
    display_name: str
    avatar: AvatarView
    games_played: int
    total_rounds: int
    best_score: int
    total_score: int
    average_distance: float | None


class LeaderboardResponse(BaseModel):
    """Таблица целиком плюс строка текущего игрока, если он в неё попадает."""

    metric: LeaderboardMetric
    #: Условия, по которым отобраны партии. Повторяются в ответе, чтобы клиент
    #: мог убедиться, что показывает именно то, что просил
    difficulty: Difficulty | None
    continent: Continent | None
    country_group: CountryGroup | None

    entries: list[LeaderboardEntry]
    me: LeaderboardEntry | None
