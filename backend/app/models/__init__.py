"""Импорт всех моделей, чтобы Alembic видел таблицы при автогенерации."""

from app.models.enums import GameMode, RoundStatus, SessionStatus, ZoneCategory
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.models.user import User

__all__ = [
    "GameMode",
    "GameSession",
    "LocationZone",
    "Round",
    "RoundStatus",
    "SessionStatus",
    "User",
    "ZoneCategory",
]
