"""Импорт всех моделей, чтобы Alembic видел таблицы при автогенерации."""

from app.models.avatar_image import AvatarImage
from app.models.country import Country
from app.models.daily import DailyChallenge
from app.models.enums import (
    Continent,
    FeedbackKind,
    FriendshipStatus,
    MatchStatus,
    RoundStatus,
    SessionStatus,
    ZoneCategory,
)
from app.models.feedback import Feedback
from app.models.friendship import Friendship
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.match import Match
from app.models.round import Round
from app.models.series import RoundSeries, SeriesRound
from app.models.user import User

__all__ = [
    "AvatarImage",
    "Continent",
    "Country",
    "DailyChallenge",
    "Feedback",
    "FeedbackKind",
    "Friendship",
    "FriendshipStatus",
    "GameSession",
    "LocationZone",
    "Match",
    "MatchStatus",
    "Round",
    "RoundSeries",
    "RoundStatus",
    "SeriesRound",
    "SessionStatus",
    "User",
    "ZoneCategory",
]
