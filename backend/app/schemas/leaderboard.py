"""Схемы таблицы лидеров."""

from pydantic import BaseModel

from app.services.leaderboard import LeaderboardMetric


class LeaderboardEntry(BaseModel):
    """Игрок и его место."""

    rank: int
    user_id: int
    display_name: str
    games_played: int
    total_rounds: int
    best_score: int
    total_score: int
    average_distance: float | None


class LeaderboardResponse(BaseModel):
    """Таблица целиком плюс строка текущего игрока, если он в неё попадает."""

    metric: LeaderboardMetric
    entries: list[LeaderboardEntry]
    me: LeaderboardEntry | None
