"""
Жизненный цикл игры: сессии, раунды, приём догадок.

Всё, что связано с правилами, происходит здесь. Роутеры только разбирают
запрос и отдают ответ.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import RoundStatus, SessionStatus
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.match import Match
from app.models.round import Round
from app.models.user import User
from app.services import daily, matches, tiles
from app.services import series as series_service
from app.services import zones as zones_service
from app.services.round_timer import deadline_for, is_late, time_left_fraction
from app.services.scoring import MAX_ROUND_SCORE, evaluate_guess
from app.utils.geo import lonlat_to_tile, tile_center, tile_width_km, zoom_for_extent

logger = logging.getLogger(__name__)


async def start_session(
    db: AsyncSession,
    user: User,
    rounds_total: int,
    view_extent_km: float,
    difficulty: int | None = None,
    category: str | None = None,
    continent: str | None = None,
    zone_id: int | None = None,
    time_limit_seconds: int | None = None,
) -> tuple[GameSession, Round]:
    """
    Создать сессию и первый раунд.

    Незавершённая партия у игрока может быть только одна: начиная новую, он
    бросает предыдущую. Иначе сессии копились бы в базе, а «продолжить» не
    знало бы, какую именно продолжать.
    """
    previous = await current_session(db, user)
    if previous is not None:
        await finish_session(db, previous)

    session = GameSession(
        user_id=user.id,
        rounds_total=rounds_total,
        time_limit_seconds=time_limit_seconds,
    )
    db.add(session)
    await db.flush()

    round_obj = await create_round(
        db,
        session,
        view_extent_km,
        difficulty,
        category,
        continent,
        zone_id,
    )

    logger.info("Сессия %s начата пользователем %s", session.id, user.id)
    return session, round_obj


async def start_daily_challenge(
    db: AsyncSession,
    user: User,
    day: date,
) -> tuple[GameSession, Round]:
    """
    Начать челлендж дня.

    Правило «одна незавершённая партия» общее для обычной игры и челленджа,
    поэтому предыдущая партия закрывается так же.
    """
    previous = await current_session(db, user)
    if previous is not None:
        await finish_session(db, previous)

    try:
        return await daily.start(db, user, day)
    except IntegrityError as e:
        # Уникальный индекс на (user_id, challenge_day): игрок успел начать
        # челлендж в другой вкладке
        await db.rollback()
        raise ConflictError("Челлендж этого дня уже сыгран") from e


async def start_match(
    db: AsyncSession,
    user: User,
    match: Match,
) -> tuple[GameSession, Round]:
    """
    Войти в комнату мультиплеера.

    Правило «одна незавершённая партия» общее для всех режимов, поэтому
    предыдущая партия закрывается так же, как при обычном старте.
    """
    previous = await current_session(db, user)
    if previous is not None:
        await finish_session(db, previous)

    try:
        return await matches.join(db, match, user)
    except IntegrityError as e:
        # Частичный уникальный индекс на (user_id, match_code): игрок успел
        # войти в комнату из другой вкладки
        await db.rollback()
        raise ConflictError("Ты уже играл в этой комнате") from e


async def create_round(
    db: AsyncSession,
    session: GameSession,
    view_extent_km: float,
    difficulty: int | None = None,
    category: str | None = None,
    continent: str | None = None,
    zone_id: int | None = None,
) -> Round:
    """
    Сгенерировать раунд.

    Внутри зоны выбирается случайная точка, под неё подбирается тайл нужного
    масштаба, и целью раунда становится центр этого тайла — именно его игрок
    и видит в центре снимка.
    """
    zone = (
        await zones_service.get_zone(db, zone_id)
        if zone_id is not None
        else await zones_service.pick_random_zone(db, difficulty, category, continent)
    )

    lon, lat = await zones_service.random_point_in_zone(db, zone)

    zoom = zoom_for_extent(lat, view_extent_km, max_zoom=settings.satellite_max_zoom - 1)
    tile_x, tile_y = lonlat_to_tile(lon, lat, zoom)
    target_lon, target_lat = tile_center(tile_x, tile_y, zoom)

    round_obj = Round(
        session_id=session.id,
        position=session.rounds_done + 1,
        zone_id=zone.id,
        target_point=WKTElement(f"POINT({target_lon} {target_lat})", srid=4326),
        tile_zoom=zoom,
        tile_x=tile_x,
        tile_y=tile_y,
        status=RoundStatus.ACTIVE,
        view_extent_km=Decimal(str(round(tile_width_km(tile_x, tile_y, zoom), 3))),
        max_score=MAX_ROUND_SCORE,
        deadline_at=deadline_for(session),
    )
    db.add(round_obj)

    await db.flush()
    await db.refresh(round_obj, ["zone"])

    tiles.schedule_prewarm(round_obj)

    logger.info("Раунд %s создан в зоне %s (зум %s)", round_obj.id, zone.id, zoom)
    return round_obj


async def submit_guess(
    db: AsyncSession,
    user: User,
    round_obj: Round,
    longitude: float,
    latitude: float,
) -> tuple[Round, Round | None]:
    """
    Принять догадку: посчитать расстояние и очки, выдать следующий раунд.

    Возвращает завершённый раунд и следующий, если сессия не закончилась.
    """
    if not round_obj.is_open:
        raise ConflictError("Догадка по этому раунду уже принята")

    session = round_obj.session
    if not session.is_active:
        raise ConflictError("Сессия уже завершена")

    if is_late(round_obj):
        # Ответ опоздал: раунд закрывается нулём, но партия продолжается
        return await _close_timed_out(db, round_obj)

    target_lon, target_lat = await target_coordinates(db, round_obj)

    result = evaluate_guess(
        guess_lon=longitude,
        guess_lat=latitude,
        target_lon=target_lon,
        target_lat=target_lat,
        view_extent_km=float(round_obj.view_extent_km),
        max_score=round_obj.max_score,
        time_left_fraction=time_left_fraction(session, round_obj),
    )

    round_obj.guess_point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
    round_obj.distance_km = Decimal(str(result.distance_km))
    round_obj.accuracy_percentage = Decimal(str(result.accuracy))
    round_obj.score = result.score
    round_obj.status = RoundStatus.GUESSED
    round_obj.guessed_at = datetime.now(UTC)
    round_obj.answer_seconds = _elapsed(round_obj)

    session.rounds_done += 1
    session.total_score += result.score
    session.average_score = session.total_score / session.rounds_done

    await db.flush()

    next_round = await _advance(db, session)
    await _update_zone_statistics(db, round_obj.zone_id)

    logger.info(
        "Раунд %s: %s км, %s очков (пользователь %s)",
        round_obj.id,
        result.distance_km,
        result.score,
        user.id,
    )
    return round_obj, next_round


async def timeout_round(
    db: AsyncSession,
    round_obj: Round,
) -> tuple[Round, Round | None]:
    """
    Закрыть раунд, на который не успели ответить.

    Клиент зовёт это, когда таймер дошёл до нуля, а точка не поставлена.
    Сервер проверяет, что срок действительно вышел: иначе это был бы
    бесплатный пропуск неудобного раунда.
    """
    if not round_obj.is_open:
        raise ConflictError("Раунд уже закрыт")
    if not round_obj.session.is_active:
        raise ConflictError("Сессия уже завершена")
    if not is_late(round_obj):
        raise ConflictError("Время ещё не вышло")

    return await _close_timed_out(db, round_obj)


async def _close_timed_out(db: AsyncSession, round_obj: Round) -> tuple[Round, Round | None]:
    """Раунд без ответа: ноль очков, партия идёт дальше."""
    session = round_obj.session

    round_obj.status = RoundStatus.TIMED_OUT
    round_obj.score = 0
    round_obj.guessed_at = datetime.now(UTC)
    round_obj.answer_seconds = _elapsed(round_obj)

    session.rounds_done += 1
    session.average_score = session.total_score / session.rounds_done

    await db.flush()

    next_round = await _advance(db, session)
    await _update_zone_statistics(db, round_obj.zone_id)

    logger.info("Раунд %s закрыт по времени", round_obj.id)
    return round_obj, next_round


async def _advance(db: AsyncSession, session: GameSession) -> Round | None:
    """Следующий раунд партии или ничего, если она закончилась."""
    if session.rounds_done >= session.rounds_total:
        await finish_session(db, session)
        return None

    if session.series_id is not None:
        return await series_service.open_round(db, session, session.rounds_done + 1)

    previous = await _first_round(db, session)
    return await create_round(db, session, view_extent_km=float(previous.view_extent_km))


def _elapsed(round_obj: Round) -> Decimal:
    """Сколько секунд прошло с начала раунда."""
    seconds = (datetime.now(UTC) - round_obj.created_at).total_seconds()
    return Decimal(str(round(max(seconds, 0.0), 2)))


async def finish_session(db: AsyncSession, session: GameSession) -> GameSession:
    """Завершить сессию и пересчитать статистику игрока."""
    if not session.is_active:
        return session

    session.status = (
        SessionStatus.FINISHED
        if session.rounds_done >= session.rounds_total
        else SessionStatus.ABANDONED
    )
    session.finished_at = datetime.now(UTC)

    await db.flush()
    await _update_user_statistics(db, session.user_id)

    logger.info("Сессия %s завершена со счётом %s", session.id, session.total_score)
    return session


async def get_session_for_user(db: AsyncSession, user: User, session_id: str) -> GameSession:
    """Сессия пользователя. Чужая сессия — 403, несуществующая — 404."""
    # Идентификатор из адреса может быть каким угодно. Не проверив формат, мы
    # уронили бы запрос в драйвере с пятисоткой вместо честного «не найдено».
    try:
        uuid.UUID(session_id)
    except ValueError as e:
        raise NotFoundError(f"Сессия {session_id} не найдена") from e

    # populate_existing: за время запроса у сессии мог появиться новый раунд, а
    # без этого SQLAlchemy вернул бы объект из карты идентичности со старым
    # списком раундов.
    stmt = (
        select(GameSession)
        .where(GameSession.id == session_id)
        .options(selectinload(GameSession.rounds).selectinload(Round.zone))
        .execution_options(populate_existing=True)
    )
    session = (await db.execute(stmt)).scalar_one_or_none()

    if session is None:
        raise NotFoundError(f"Сессия {session_id} не найдена")
    if session.user_id != user.id:
        raise ForbiddenError("Это чужая сессия")

    return session


async def list_sessions(
    db: AsyncSession,
    user: User,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[GameSession], int]:
    """Партии игрока, новые сверху, вместе с общим количеством."""
    condition = GameSession.user_id == user.id

    total = (await db.execute(select(func.count(GameSession.id)).where(condition))).scalar_one()

    sessions = (
        (
            await db.execute(
                select(GameSession)
                .where(condition)
                .order_by(GameSession.started_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )

    return list(sessions), int(total)


async def current_session(db: AsyncSession, user: User) -> GameSession | None:
    """Незавершённая партия игрока, чтобы можно было продолжить с того же места."""
    stmt = (
        select(GameSession)
        .where(GameSession.user_id == user.id, GameSession.status == SessionStatus.ACTIVE)
        .options(selectinload(GameSession.rounds).selectinload(Round.zone))
        .order_by(GameSession.started_at.desc())
        .limit(1)
        .execution_options(populate_existing=True)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_round_for_user(
    db: AsyncSession,
    user: User,
    round_id: int,
    *,
    for_update: bool = False,
) -> Round:
    """
    Раунд пользователя. Чужой раунд — 403, несуществующий — 404.

    for_update блокирует строку раунда до конца транзакции. Это нужно там, где
    раунд закрывается: две одновременные догадки по одному раунду иначе обе
    прошли бы проверку «раунд ещё открыт» и очки засчитались бы дважды.
    """
    stmt = (
        select(Round)
        .where(Round.id == round_id)
        .options(selectinload(Round.session), selectinload(Round.zone))
    )
    if for_update:
        stmt = stmt.with_for_update()

    round_obj = (await db.execute(stmt)).scalar_one_or_none()

    if round_obj is None:
        raise NotFoundError(f"Раунд {round_id} не найден")
    if round_obj.session.user_id != user.id:
        raise ForbiddenError("Это чужой раунд")

    return round_obj


async def active_round(db: AsyncSession, session: GameSession) -> Round | None:
    """Текущий незавершённый раунд сессии."""
    stmt = (
        select(Round)
        .where(Round.session_id == session.id, Round.status == RoundStatus.ACTIVE)
        .options(selectinload(Round.zone))
        .order_by(Round.position.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def target_coordinates(db: AsyncSession, round_obj: Round) -> tuple[float, float]:
    """Координаты цели раунда. Читаются из PostGIS, а не из geometry-объекта."""
    stmt = select(
        func.ST_X(Round.target_point),
        func.ST_Y(Round.target_point),
    ).where(Round.id == round_obj.id)

    row = (await db.execute(stmt)).one()
    return float(row[0]), float(row[1])


async def guess_coordinates(db: AsyncSession, round_obj: Round) -> tuple[float, float] | None:
    """Координаты догадки, если она была сделана."""
    if round_obj.guess_point is None:
        return None

    stmt = select(
        func.ST_X(Round.guess_point),
        func.ST_Y(Round.guess_point),
    ).where(Round.id == round_obj.id)

    row = (await db.execute(stmt)).one()
    return float(row[0]), float(row[1])


async def _first_round(db: AsyncSession, session: GameSession) -> Round:
    """Первый раунд сессии — по нему выравнивается масштаб остальных."""
    stmt = select(Round).where(Round.session_id == session.id, Round.position == 1)
    return (await db.execute(stmt)).scalar_one()


async def _update_user_statistics(db: AsyncSession, user_id: int) -> None:
    """Пересчитать статистику игрока по завершённым сессиям."""
    finished = select(GameSession.id).where(
        GameSession.user_id == user_id,
        GameSession.status.in_([SessionStatus.FINISHED, SessionStatus.ABANDONED]),
    )

    totals = (
        await db.execute(
            select(
                func.count(GameSession.id),
                func.coalesce(func.sum(GameSession.total_score), 0),
                func.coalesce(func.max(GameSession.total_score), 0),
            ).where(GameSession.id.in_(finished))
        )
    ).one()

    rounds = (
        await db.execute(
            select(
                func.count(Round.id),
                func.avg(Round.score),
                func.avg(Round.distance_km),
            ).where(
                Round.session_id.in_(finished),
                Round.status == RoundStatus.GUESSED,
            )
        )
    ).one()

    user = await db.get(User, user_id)
    if user is None:
        return

    user.games_played = int(totals[0])
    user.total_score = int(totals[1])
    user.best_score = int(totals[2])
    user.total_rounds = int(rounds[0])
    user.average_score = float(rounds[1]) if rounds[1] is not None else None
    user.average_distance = float(rounds[2]) if rounds[2] is not None else None
    user.updated_at = datetime.now(UTC)


async def _update_zone_statistics(db: AsyncSession, zone_id: int) -> None:
    """Пересчитать среднее по зоне после завершённого раунда."""
    stats = (
        await db.execute(
            select(
                func.count(Round.id),
                func.avg(Round.score),
                func.avg(Round.distance_km),
            ).where(Round.zone_id == zone_id, Round.status == RoundStatus.GUESSED)
        )
    ).one()

    zone = await db.get(LocationZone, zone_id)
    if zone is None:
        return

    zone.total_rounds = int(stats[0])
    zone.average_score = float(stats[1]) if stats[1] is not None else None
    zone.average_distance = float(stats[2]) if stats[2] is not None else None
    zone.updated_at = datetime.now(UTC)
