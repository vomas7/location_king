# Импортируем все модели, чтобы Alembic их видел при автогенерации миграций
from app.models.game_session import GameSession, GameMode, SessionStatus
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.models.user import User

__all__ = [
    "User",
    "LocationZone",
    "GameSession",
    "GameMode",
    "SessionStatus",
    "Round",
]
