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
from app.schemas.game import RoundResult, RoundView, SessionView, ZoneView
from app.services import game as game_service


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


def round_view(round_obj: Round, index: int) -> RoundView:
    """Активный раунд: адрес прокси тайлов вместо координат."""
    return RoundView(
        id=round_obj.id,
        index=index,
        status=round_obj.status,
        view_extent_km=round_obj.view_extent_km,
        max_zoom=game_service.max_local_zoom(round_obj),
        tiles_url=f"/api/rounds/{round_obj.id}/tiles/{{z}}/{{x}}/{{y}}.jpg",
        attribution=settings.satellite_attribution,
        created_at=round_obj.created_at,
    )


async def round_result(db: AsyncSession, round_obj: Round, index: int) -> RoundResult:
    """Завершённый раунд вместе с координатами цели."""
    target = await game_service.target_coordinates(db, round_obj)
    guess = await game_service.guess_coordinates(db, round_obj)

    return RoundResult(
        id=round_obj.id,
        index=index,
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
        rounds_total=session.rounds_total,
        rounds_done=session.rounds_done,
        total_score=session.total_score,
        average_score=session.average_score,
        started_at=session.started_at,
        finished_at=session.finished_at,
    )


async def session_results(db: AsyncSession, rounds: list[Round]) -> list[RoundResult]:
    """История завершённых раундов сессии по порядку."""
    return [
        await round_result(db, round_obj, index)
        for index, round_obj in enumerate(sorted(rounds, key=lambda r: r.id), start=1)
        if round_obj.status == RoundStatus.GUESSED
    ]


def round_index(session: GameSession, round_obj: Round) -> int:
    """Порядковый номер раунда в сессии, начиная с единицы."""
    ordered = sorted(session.rounds, key=lambda r: r.id)
    return next(i for i, r in enumerate(ordered, start=1) if r.id == round_obj.id)
