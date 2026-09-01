"""
Комнаты мультиплеера.

Хост создаёт комнату, получает короткий код и раздаёт ссылку. Все участники
играют одну и ту же серию раундов — каждый в своём темпе — и в конце
сравнивают результаты.

Живого обмена ходами здесь нет намеренно: он потребовал бы соединения, которое
рвётся вместе с вкладкой, а сравнивать результаты можно и после.
"""

import logging
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import AnswerMode, MatchKind, MatchStatus, SessionStatus
from app.models.game_session import GameSession
from app.models.match import Match
from app.models.round import Round
from app.models.user import User
from app.services import series as series_service
from app.utils import codes

logger = logging.getLogger(__name__)

# Сколько попыток на подбор свободного кода, прежде чем признать неудачу
CODE_ATTEMPTS = 10


async def create(
    db: AsyncSession,
    host: User,
    rounds_total: int,
    view_extent_km: float | None,
    category: str | None = None,
    continent: str | None = None,
    country_group: str | None = None,
    difficulty: str | None = None,
    time_limit_seconds: int | None = None,
    kind: str = MatchKind.ROOM,
    answer_mode: str = AnswerMode.POINT,
) -> Match:
    """Собрать комнату вместе с её серией раундов."""
    series = await series_service.create(
        db,
        rounds_total,
        view_extent_km,
        category,
        continent,
        country_group,
        difficulty,
        answer_mode=answer_mode,
    )

    for _ in range(CODE_ATTEMPTS):
        match = Match(
            code=codes.new_code(),
            # Связь, а не только идентификатор: иначе показать имя хоста сразу
            # после создания не выйдет — ленивая подгрузка в async запрещена
            host=host,
            series_id=series.id,
            rounds_total=rounds_total,
            time_limit_seconds=time_limit_seconds,
            status=MatchStatus.OPEN,
            kind=kind,
        )

        try:
            # Точка сохранения, а не транзакция целиком: откат из-за занятого
            # кода не должен уносить с собой только что собранную серию
            async with db.begin_nested():
                db.add(match)
                await db.flush()
        except IntegrityError:
            logger.info("Код %s занят, берём следующий", match.code)
            continue

        logger.info("Комната %s создана игроком %s", match.code, host.id)
        return match

    raise ConflictError("Не удалось подобрать свободный код комнаты")


async def get(db: AsyncSession, code: str) -> Match:
    """Комната по коду. Регистр кода не важен."""
    stmt = select(Match).where(Match.code == code.strip().upper()).options(selectinload(Match.host))
    match = (await db.execute(stmt)).scalar_one_or_none()

    if match is None:
        raise NotFoundError(f"Комната {code} не найдена")
    return match


async def join(db: AsyncSession, match: Match, user: User) -> tuple[GameSession, Round]:
    """Присоединиться к комнате и получить первый раунд."""
    if match.status != MatchStatus.OPEN:
        raise ConflictError("Набор в эту комнату закрыт")
    if await session_of(db, match, user) is not None:
        raise ConflictError("Ты уже играл в этой комнате")

    session = GameSession(
        user_id=user.id,
        rounds_total=match.rounds_total,
        time_limit_seconds=match.time_limit_seconds,
        match_code=match.code,
        series_id=match.series_id,
    )
    db.add(session)
    await db.flush()

    first = await series_service.open_round(db, session, position=1)
    logger.info("Игрок %s вошёл в комнату %s", user.id, match.code)

    return session, first


async def close(db: AsyncSession, match: Match, user: User) -> Match:
    """Закрыть набор. Может только хост."""
    if match.host_user_id != user.id:
        raise ForbiddenError("Закрыть комнату может только тот, кто её создал")

    match.status = MatchStatus.CLOSED
    await db.flush()

    return match


async def session_of(db: AsyncSession, match: Match, user: User) -> GameSession | None:
    """Партия игрока в этой комнате, если он уже входил."""
    stmt = select(GameSession).where(
        GameSession.match_code == match.code,
        GameSession.user_id == user.id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def standings(db: AsyncSession, match: Match) -> list[GameSession]:
    """
    Кто как сыграл.

    Сначала те, кто дошёл до конца, — по убыванию счёта; следом те, кто ещё
    играет, чтобы было видно, кого ждать.
    """
    stmt = (
        select(GameSession)
        .where(GameSession.match_code == match.code)
        .options(selectinload(GameSession.user))
        .order_by(
            (GameSession.status != SessionStatus.FINISHED),
            GameSession.total_score.desc(),
            GameSession.finished_at,
        )
    )
    return list((await db.execute(stmt)).scalars().all())


async def hosted_recently(db: AsyncSession, user: User, limit: int = 5) -> list[Match]:
    """Последние комнаты, созданные игроком."""
    stmt = (
        select(Match)
        .where(Match.host_user_id == user.id)
        .order_by(Match.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def player_counts(db: AsyncSession, codes: Sequence[str]) -> dict[str, int]:
    """Сколько игроков вошло в каждую из комнат — одним запросом на список."""
    if not codes:
        return {}

    stmt = (
        select(GameSession.match_code, func.count(GameSession.id))
        .where(GameSession.match_code.in_(codes))
        .group_by(GameSession.match_code)
    )
    rows = (await db.execute(stmt)).all()

    return {code: count for code, count in rows if code is not None}
