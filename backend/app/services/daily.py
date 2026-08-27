"""
Челлендж дня: одна серия раундов на сутки, одинаковая для всех.

Серия создаётся при первом обращении за день и дальше не меняется — иначе
двое, начавшие игру в разное время, играли бы в разное и сравнивать их
результаты было бы нельзя.

Границы суток считаются в UTC: игрокам из разных часовых поясов достаётся один
и тот же челлендж, а день сменяется у всех одновременно.
"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import ConflictError
from app.models.daily import DailyChallenge, DailyRound
from app.models.enums import SessionStatus
from app.models.game_session import GameSession
from app.models.round import Round
from app.models.user import User
from app.services import tiles
from app.services import zones as zones_service
from app.services.round_timer import deadline_for
from app.services.scoring import MAX_ROUND_SCORE
from app.utils.geo import lonlat_to_tile, tile_center, tile_width_km, zoom_for_extent

logger = logging.getLogger(__name__)

# Условия челленджа одинаковы каждый день: сравнивать результаты можно только
# при равных правилах
ROUNDS_TOTAL = 5
VIEW_EXTENT_KM = 5.0


def today() -> date:
    """Текущий день челленджа."""
    return datetime.now(UTC).date()


async def get_or_create(db: AsyncSession, day: date) -> DailyChallenge:
    """Челлендж дня. Если его ещё нет — собрать и сохранить."""
    existing = await _load(db, day)
    if existing is not None:
        return existing

    # Раунды кладутся сразу в связь, а не отдельными объектами: иначе
    # обращение к challenge.rounds ниже полезло бы в базу за уже созданным.
    rounds = [await _build_round(db, day, position) for position in range(1, ROUNDS_TOTAL + 1)]
    challenge = DailyChallenge(day=day, rounds=rounds)
    db.add(challenge)

    try:
        await db.flush()
    except IntegrityError:
        # Два первых игрока дня могли начать одновременно: побеждает тот, кто
        # успел записать, второй просто читает готовое.
        await db.rollback()
        created = await _load(db, day)
        if created is None:
            raise
        return created

    logger.info("Челлендж на %s собран", day)
    return challenge


async def start(db: AsyncSession, user: User, day: date) -> tuple[GameSession, Round]:
    """Начать челлендж дня. Второй раз за день — конфликт."""
    if await played_session(db, user, day) is not None:
        raise ConflictError("Челлендж этого дня уже сыгран")

    challenge = await get_or_create(db, day)

    session = GameSession(
        user_id=user.id,
        rounds_total=ROUNDS_TOTAL,
        challenge_day=day,
    )
    db.add(session)
    await db.flush()

    first = await open_round(db, session, challenge, position=1)
    logger.info("Игрок %s начал челлендж %s", user.id, day)

    return session, first


async def open_round(
    db: AsyncSession,
    session: GameSession,
    challenge: DailyChallenge,
    position: int,
) -> Round:
    """Скопировать заготовку челленджа в раунд игрока."""
    template = next((item for item in challenge.rounds if item.position == position), None)
    if template is None:
        raise ConflictError(f"В челлендже {challenge.day} нет раунда {position}")

    round_obj = Round(
        session_id=session.id,
        position=position,
        zone_id=template.zone_id,
        target_point=template.target_point,
        tile_zoom=template.tile_zoom,
        tile_x=template.tile_x,
        tile_y=template.tile_y,
        view_extent_km=template.view_extent_km,
        max_score=MAX_ROUND_SCORE,
        deadline_at=deadline_for(session),
    )
    db.add(round_obj)

    await db.flush()
    await db.refresh(round_obj, ["zone"])

    tiles.schedule_prewarm(round_obj)

    return round_obj


async def played_session(db: AsyncSession, user: User, day: date) -> GameSession | None:
    """Партия игрока по челленджу этого дня, если он его уже начинал."""
    stmt = select(GameSession).where(
        GameSession.user_id == user.id,
        GameSession.challenge_day == day,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def results(db: AsyncSession, day: date, limit: int = 20) -> list[GameSession]:
    """Таблица дня: завершённые партии по убыванию счёта."""
    stmt = (
        select(GameSession)
        .where(
            GameSession.challenge_day == day,
            GameSession.status == SessionStatus.FINISHED,
        )
        .options(selectinload(GameSession.user))
        .order_by(GameSession.total_score.desc(), GameSession.finished_at)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _load(db: AsyncSession, day: date) -> DailyChallenge | None:
    stmt = (
        select(DailyChallenge)
        .where(DailyChallenge.day == day)
        .options(selectinload(DailyChallenge.rounds))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _build_round(db: AsyncSession, day: date, position: int) -> DailyRound:
    """Собрать заготовку раунда так же, как это делает обычная игра."""
    zone = await zones_service.pick_random_zone(db)
    lon, lat = await zones_service.random_point_in_zone(db, zone)

    zoom = zoom_for_extent(lat, VIEW_EXTENT_KM, max_zoom=settings.satellite_max_zoom - 1)
    tile_x, tile_y = lonlat_to_tile(lon, lat, zoom)
    target_lon, target_lat = tile_center(tile_x, tile_y, zoom)

    return DailyRound(
        day=day,
        position=position,
        zone_id=zone.id,
        target_point=WKTElement(f"POINT({target_lon} {target_lat})", srid=4326),
        tile_zoom=zoom,
        tile_x=tile_x,
        tile_y=tile_y,
        view_extent_km=Decimal(str(round(tile_width_km(tile_x, tile_y, zoom), 3))),
    )


async def played_count(db: AsyncSession, day: date) -> int:
    """Сколько игроков уже завершили челлендж дня."""
    stmt = select(func.count(GameSession.id)).where(
        GameSession.challenge_day == day,
        GameSession.status == SessionStatus.FINISHED,
    )
    return int((await db.execute(stmt)).scalar_one())
