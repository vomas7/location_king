"""
Test schemas for debugging.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class TestRoundResponse(BaseModel):
    """Упрощённая информация о раунде для тестирования"""
    id: int
    session_id: str
    target_point: dict  # GeoJSON Point
    status: str
    max_score: int
    time_limit_seconds: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
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
    time_control: Optional[str]
    view_extent_km: int
    current_round: Optional[TestRoundResponse]
    
    class Config:
        from_attributes = True