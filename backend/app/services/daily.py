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

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ConflictError
from app.models.daily import DailyChallenge
from app.models.enums import SessionStatus
from app.models.game_session import GameSession
from app.models.round import Round
from app.models.user import User
from app.services import series as series_service

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

    series = await series_service.create(db, ROUNDS_TOTAL, VIEW_EXTENT_KM)
    challenge = DailyChallenge(day=day, series_id=series.id)
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
        series_id=challenge.series_id,
    )
    db.add(session)
    await db.flush()

    first = await series_service.open_round(db, session, position=1)
    logger.info("Игрок %s начал челлендж %s", user.id, day)

    return session, first


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


async def played_count(db: AsyncSession, day: date) -> int:
    """Сколько игроков уже завершили челлендж дня."""
    stmt = select(func.count(GameSession.id)).where(
        GameSession.challenge_day == day,
        GameSession.status == SessionStatus.FINISHED,
    )
    return int((await db.execute(stmt)).scalar_one())


async def _load(db: AsyncSession, day: date) -> DailyChallenge | None:
    stmt = select(DailyChallenge).where(DailyChallenge.day == day)
    return (await db.execute(stmt)).scalar_one_or_none()
