"""
Сборка ответов API из моделей.

Вынесено из роутеров, потому что раунд и сессию отдают три разных эндпоинта, а
правило «до догадки координат в ответе нет» должно быть записано один раз.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.enums import RoundStatus, category_name, difficulty_name
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.schemas.daily import DailyResult
from app.schemas.game import RoundResult, RoundView, SessionSummary, SessionView, ZoneView
from app.schemas.leaderboard import LeaderboardEntry
from app.services import game as game_service
from app.services.leaderboard import LeaderboardRow


def zone_view(zone: LocationZone) -> ZoneView:
    """Публичное представление зоны."""
    return ZoneView(
        id=zone.id,
        name=zone.name,
        description=zone.description,
        difficulty=zone.difficulty,
        difficulty_name=difficulty_name(zone.difficulty),
        category=zone.category,
        category_name=category_name(zone.category),
        country=zone.country,
        region=zone.region,
        tags=zone.tag_list,
    )


def round_view(round_obj: Round) -> RoundView:
    """Активный раунд: адрес прокси тайлов вместо координат."""
    return RoundView(
        id=round_obj.id,
        index=round_obj.position,
        status=round_obj.status,
        view_extent_km=round_obj.view_extent_km,
        max_zoom=game_service.max_local_zoom(round_obj),
        tiles_url=f"/api/rounds/{round_obj.id}/tiles/{{z}}/{{x}}/{{y}}.jpg",
        attribution=settings.satellite_attribution,
        created_at=round_obj.created_at,
    )


async def round_result(db: AsyncSession, round_obj: Round) -> RoundResult:
    """Завершённый раунд вместе с координатами цели."""
    target = await game_service.target_coordinates(db, round_obj)
    guess = await game_service.guess_coordinates(db, round_obj)

    return RoundResult(
        id=round_obj.id,
        index=round_obj.position,
        status=round_obj.status,
        view_extent_km=round_obj.view_extent_km,
        target=target,
        guess=guess,
        distance_km=round_obj.distance_km,
        score=round_obj.score,
        max_score=round_obj.max_score,
        accuracy=round_obj.accuracy_percentage,
        zone=zone_view(round_obj.zone),
        guessed_at=round_obj.guessed_at,
    )


def session_view(session: GameSession) -> SessionView:
    """Состояние партии."""
    return SessionView(
        id=session.id,
        status=session.status,
        challenge_day=session.challenge_day,
        rounds_total=session.rounds_total,
        rounds_done=session.rounds_done,
        total_score=session.total_score,
        average_score=session.average_score,
        started_at=session.started_at,
        finished_at=session.finished_at,
    )


async def session_results(db: AsyncSession, rounds: list[Round]) -> list[RoundResult]:
    """История завершённых раундов сессии по порядку."""
    played = sorted(
        (item for item in rounds if item.status == RoundStatus.GUESSED),
        key=lambda item: item.position,
    )
    return [await round_result(db, round_obj) for round_obj in played]


def session_summary(session: GameSession) -> SessionSummary:
    """Партия в списке истории."""
    return SessionSummary(
        id=session.id,
        status=session.status,
        challenge_day=session.challenge_day,
        rounds_total=session.rounds_total,
        rounds_done=session.rounds_done,
        total_score=session.total_score,
        started_at=session.started_at,
        finished_at=session.finished_at,
    )


def leaderboard_entry(row: LeaderboardRow) -> LeaderboardEntry:
    """Строка таблицы лидеров."""
    return LeaderboardEntry(
        rank=row.rank,
        user_id=row.user.id,
        display_name=row.user.display_name or row.user.username,
        games_played=row.user.games_played,
        total_rounds=row.user.total_rounds,
        best_score=row.user.best_score,
        total_score=row.user.total_score,
        average_distance=row.user.average_distance,
    )


def session_summary_or_none(session: GameSession | None) -> SessionSummary | None:
    """Партия в списке истории или ничего, если её нет."""
    return None if session is None else session_summary(session)


def daily_result(rank: int, session: GameSession) -> DailyResult:
    """Строка таблицы челленджа дня."""
    return DailyResult(
        rank=rank,
        display_name=session.user.display_name or session.user.username,
        total_score=session.total_score,
        finished_at=session.finished_at,
    )
