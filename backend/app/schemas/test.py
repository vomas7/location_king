"""
Test schemas for debugging.
"""

from datetime import datetime

from pydantic import BaseModel


class TestRoundResponse(BaseModel):
    """Упрощённая информация о раунде для тестирования"""

    id: int
    session_id: str
    target_point: dict  # GeoJSON Point
    status: str
    max_score: int
    time_limit_seconds: int | None
    started_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True


class TestSessionResponse(BaseModel):
    """Упрощённая информация о сессии для тестирования"""

    id: str
    user_id: int
    rounds_total: int
    rounds_done: int
    total_score: int
    status: str
    game_mode: str
    time_control: str | None
    view_extent_km: int
    current_round: TestRoundResponse | None

    class Config:
        from_attributes = True
