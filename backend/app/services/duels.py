"""
Дуэли: подбор соперника и рейтинг по итогу.

Дуэль — это обычная комната на двоих, которую собрал сервер. Всё остальное уже
написано: серия раундов общая, партии считаются так же, таблица результатов
та же. Новое здесь ровно две вещи — как находят пару и что происходит с
рейтингом.

Формат дуэли фиксирован намеренно. Рейтинг сравнивает игроков между собой, и
это работает, только пока все дуэли устроены одинаково: разрешив выбирать
уровень, мы вернули бы ту же беду, из-за которой рейтинг нельзя считать по
обычным партиям.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import messages
from app.exceptions import ConflictError, NotFoundError
from app.models.enums import Difficulty, MatchKind, SessionStatus
from app.models.game_session import GameSession
from app.models.match import Match
from app.models.user import User
from app.observability import metrics
from app.services import difficulty as difficulty_service
from app.services import matches as matches_service
from app.services import matchmaking
from app.utils import elo

logger = logging.getLogger(__name__)

#: Формат дуэли. Один на всех и неизменяемый: иначе рейтинги несравнимы
ROUNDS_TOTAL = 5
DIFFICULTY = Difficulty.NORMAL
#: Кадр берётся из уровня, а не задаётся отдельно: правило про кадр в игре
#: одно, и дуэль не должна оказаться труднее одиночной партии того же уровня
VIEW_EXTENT_KM = difficulty_service.view_extent_km(DIFFICULTY)
TIME_LIMIT_SECONDS = 60

#: Через сколько недоигранная дуэль считается брошенной. Без этого правила
#: рейтинг чинился бы закрытием вкладки: проигрывающий просто не доигрывал бы
ABANDON_AFTER = timedelta(minutes=10)


@dataclass(frozen=True)
class SearchState:
    """Что показать игроку, пока он ищет соперника."""

    #: Сколько человек ищет прямо сейчас, вместе с ним самим
    searching: int
    #: Код дуэли, если пара нашлась
    code: str | None


async def enter(user: User) -> SearchState:
    """Встать в очередь."""
    await matchmaking.join(user.id, user.rating)
    await metrics.count("duel_search_started")

    return SearchState(searching=len(await matchmaking.searching()), code=None)


async def count() -> int:
    """Сколько человек ищет соперника прямо сейчас."""
    return len(await matchmaking.searching())


async def leave(user: User) -> None:
    """Выйти из очереди."""
    await matchmaking.leave(user.id)


async def look(db: AsyncSession, user: User) -> SearchState:
    """
    Опрос из очереди: либо пара, либо число ищущих.

    Здесь же продлевается запись игрока — отдельного удара сердца не нужно, а
    ушедший из очереди выпадает сам.
    """
    found = await matchmaking.take_found(user.id)
    if found is not None:
        return SearchState(searching=0, code=found)

    # Очередь может отказать: пара нашлась ровно между двумя строчками выше
    if not await matchmaking.join(user.id, user.rating):
        return SearchState(searching=0, code=await matchmaking.take_found(user.id))

    code = await _try_to_pair(db, user)

    if code is not None:
        return SearchState(searching=0, code=code)

    return SearchState(searching=len(await matchmaking.searching()), code=None)


async def _try_to_pair(db: AsyncSession, user: User) -> str | None:
    """
    Подобрать пару под замком.

    Замок нужен, потому что воркеров четыре: без него двое соперников могли бы
    подобрать друг друга одновременно и создать две дуэли вместо одной.
    """
    if not await matchmaking.lock():
        return None

    try:
        now = datetime.now(UTC).timestamp()
        queue = await matchmaking.searching(now)

        seeker = next((item for item in queue if item.user_id == user.id), None)
        if seeker is None:
            return None

        opponent = matchmaking.pick_opponent(seeker, queue, now)
        if opponent is None:
            return None

        match = await matches_service.create(
            db,
            host=user,
            rounds_total=ROUNDS_TOTAL,
            view_extent_km=VIEW_EXTENT_KM,
            difficulty=DIFFICULTY,
            time_limit_seconds=TIME_LIMIT_SECONDS,
            kind=MatchKind.DUEL,
        )
        # Комната сохраняется до объявления: иначе соперник придёт за кодом,
        # которого ещё нет в базе
        await db.commit()

        await matchmaking.announce((user.id, opponent.user_id), match.code)
        await metrics.count("duel_started")
        logger.info(
            "Дуэль %s: игрок %s (%s) против %s (%s)",
            match.code,
            user.id,
            seeker.rating,
            opponent.user_id,
            opponent.rating,
        )
        return match.code
    finally:
        await matchmaking.unlock()


async def get_duel(db: AsyncSession, code: str) -> Match:
    """Дуэль по коду. Обычная комната по этому пути не проходит."""
    match = await matches_service.get(db, code)

    if match.kind != MatchKind.DUEL:
        raise NotFoundError(messages.DUEL_NOT_FOUND.format(code=code))
    return match


async def settle_for_session(db: AsyncSession, session: GameSession) -> bool:
    """
    Досчитать дуэль, к которой относится законченная партия.

    Вызывающему не нужно знать ни про комнаты, ни про то, что дуэль — одна из
    них: он сообщает, что партия закончилась, остальное решается здесь.
    """
    if session.match_code is None:
        return False

    match = await matches_service.get(db, session.match_code)
    return await settle(db, match)


async def settle(db: AsyncSession, match: Match) -> bool:
    """
    Начислить рейтинг, если дуэль доиграна.

    Возвращает True, если рейтинг начислен именно этим вызовом. Второй раз не
    начисляется: строка комнаты берётся под блокировку, а отметка о начислении
    стоит в ней же.
    """
    if match.kind != MatchKind.DUEL:
        return False

    locked = (
        await db.execute(select(Match).where(Match.code == match.code).with_for_update())
    ).scalar_one()

    if locked.rated_at is not None:
        return False

    sessions = await _sessions(db, locked)
    if len(sessions) != 2:
        return False

    outcomes = _outcomes(locked, sessions)
    if outcomes is None:
        return False

    first, second = (session.user for session in sessions)

    # Оба рейтинга считаются от того, что было до дуэли. Обновить первого, а
    # второго посчитать против нового значения — значит нарушить главное
    # свойство Эло: сколько один выиграл, столько другой проиграл
    before = (first.rating, second.rating)
    played = (first.duels_played, second.duels_played)

    first.rating = elo.updated(before[0], before[1], outcomes[0], played[0])
    second.rating = elo.updated(before[1], before[0], outcomes[1], played[1])

    first.duels_played += 1
    second.duels_played += 1

    locked.rated_at = datetime.now(UTC)
    await db.flush()

    await metrics.count("duel_rated")
    logger.info(
        "Дуэль %s сыграна: %s",
        locked.code,
        ", ".join(f"{item.user_id}={item.user.rating}" for item in sessions),
    )
    return True


def _outcomes(match: Match, sessions: list[GameSession]) -> tuple[float, float] | None:
    """
    Чем кончилась дуэль, или ничего, если она ещё идёт.

    Доиграл один, а второй пропал — победа доигравшему, но не сразу: у
    соперника есть время вернуться и доиграть.
    """
    first, second = sessions
    finished = [item.status == SessionStatus.FINISHED for item in sessions]

    if all(finished):
        if first.total_score == second.total_score:
            return 0.5, 0.5
        return (1.0, 0.0) if first.total_score > second.total_score else (0.0, 1.0)

    if datetime.now(UTC) - match.created_at < ABANDON_AFTER:
        return None

    if not any(finished):
        # Оба бросили: менять рейтинг обоим не за что
        return None

    return (1.0, 0.0) if finished[0] else (0.0, 1.0)


async def _sessions(db: AsyncSession, match: Match) -> list[GameSession]:
    """Партии обоих участников вместе с игроками — по порядку входа."""
    stmt = (
        select(GameSession)
        .where(GameSession.match_code == match.code)
        .options(selectinload(GameSession.user))
        .order_by(GameSession.started_at, GameSession.id)
    )
    return list((await db.execute(stmt)).scalars().all())


async def settle_stale(db: AsyncSession) -> int:
    """
    Досчитать дуэли, из которых игроки просто ушли.

    Обычно рейтинг начисляет тот, кто дошёл до конца последним. Если ушли оба
    или победитель закрыл вкладку, не дождавшись соперника, доиграть эту дуэль
    некому — её добирает уборка по расписанию.
    """
    edge = datetime.now(UTC) - ABANDON_AFTER

    stmt = select(Match).where(
        Match.kind == MatchKind.DUEL,
        Match.rated_at.is_(None),
        Match.created_at < edge,
    )
    stale = list((await db.execute(stmt)).scalars().all())

    settled = 0
    for match in stale:
        if await settle(db, match):
            settled += 1

    return settled


async def require_not_playing(db: AsyncSession, user: User) -> None:
    """
    Не пускать в очередь того, кто уже в дуэли.

    Иначе он бросит текущую дуэль ради новой, а соперник останется ждать
    десять минут ради победы, которой не радуются.
    """
    stmt = (
        select(GameSession)
        .join(Match, Match.code == GameSession.match_code)
        .where(
            GameSession.user_id == user.id,
            GameSession.status == SessionStatus.ACTIVE,
            Match.kind == MatchKind.DUEL,
        )
        .limit(1)
    )

    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise ConflictError(messages.DUEL_UNFINISHED)
