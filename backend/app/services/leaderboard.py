"""
Таблица лидеров.

Считается по завершённым партиям, а не по итоговым цифрам в профиле: зачёт
делится по условиям игры — уровню и месту, — а профиль знает только сумму за
всё время и разделить её обратно нельзя.

Партии, сыгранные до того, как условия начали запоминаться, попадают только в
общий зачёт: с каким уровнем их играли, теперь уже не выяснить.
"""

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SessionStatus
from app.models.game_session import GameSession
from app.models.series import RoundSeries
from app.models.user import User

# Меньше этого числа раундов статистика по точности ничего не значит
MIN_ROUNDS_FOR_ACCURACY = 5


class LeaderboardMetric(StrEnum):
    """По чему ранжируем игроков."""

    BEST = "best"  # лучшая партия, очков за раунд
    TOTAL = "total"  # сумма очков за все партии
    ACCURACY = "accuracy"  # средний промах, меньше — лучше


@dataclass(frozen=True)
class LeaderboardFilter:
    """Условия, по которым делится зачёт. Пусто — партии с любыми условиями."""

    difficulty: str | None = None
    continent: str | None = None
    country_group: str | None = None

    #: Считать только этих игроков. Пусто — считать всех. Так устроен зачёт
    #: среди друзей: тот же зачёт, но по короткому списку. Про дружбу таблица
    #: лидеров при этом не знает ничего — список ей приносят готовым
    players: tuple[int, ...] | None = None


@dataclass(frozen=True)
class LeaderboardRow:
    """Строка таблицы: игрок, его место и цифры под выбранные условия."""

    rank: int
    user: User
    games_played: int
    total_rounds: int
    best_score: int
    total_score: int
    average_distance: float | None


def _aggregated(filters: LeaderboardFilter) -> Select:
    """
    Игроки с их итогами по партиям, подходящим под условия.

    «Лучшая партия» считается в очках за раунд, а не в сумме: иначе партия из
    десяти раундов всегда обходила бы партию из трёх, и зачёт превращался бы в
    соревнование по длине.
    """
    stmt = (
        select(
            User,
            # Имена нарочно не совпадают со столбцами users: в подзапросе
            # места игрока обе стороны оказываются рядом, и одинаковые имена
            # SQLAlchemy разрешить не может
            func.count(GameSession.id).label("games"),
            func.coalesce(func.sum(GameSession.rounds_done), 0).label("rounds"),
            func.coalesce(func.max(GameSession.average_score), 0).label("best"),
            func.coalesce(func.sum(GameSession.total_score), 0).label("total"),
            func.avg(GameSession.average_distance).label("miss"),
        )
        .join(GameSession, GameSession.user_id == User.id)
        # Внешнее соединение: партия могла быть сыграна до того, как условия
        # начали запоминать, и терять её из общего зачёта незачем
        .outerjoin(RoundSeries, GameSession.series_id == RoundSeries.id)
        .where(
            User.is_active.is_(True),
            GameSession.status == SessionStatus.FINISHED,
        )
        .group_by(User.id)
    )

    for column, value in (
        (RoundSeries.difficulty, filters.difficulty),
        (RoundSeries.continent, filters.continent),
        (RoundSeries.country_group, filters.country_group),
    ):
        if value is not None:
            stmt = stmt.where(column == value)

    if filters.players is not None:
        stmt = stmt.where(User.id.in_(filters.players))

    return stmt


def _ordered(metric: LeaderboardMetric, filters: LeaderboardFilter) -> Select:
    """Тот же запрос, отсортированный по выбранной метрике."""
    stmt = _aggregated(filters)

    if metric is LeaderboardMetric.BEST:
        return stmt.order_by(func.max(GameSession.average_score).desc(), User.id)

    if metric is LeaderboardMetric.TOTAL:
        return stmt.order_by(func.sum(GameSession.total_score).desc(), User.id)

    return stmt.having(
        func.sum(GameSession.rounds_done) >= MIN_ROUNDS_FOR_ACCURACY,
        func.avg(GameSession.average_distance).is_not(None),
    ).order_by(func.avg(GameSession.average_distance).asc(), User.id)


def _row(rank: int, record: tuple) -> LeaderboardRow:
    user, games, rounds, best, total, distance = record

    return LeaderboardRow(
        rank=rank,
        user=user,
        games_played=int(games),
        total_rounds=int(rounds),
        best_score=int(best),
        total_score=int(total),
        average_distance=float(distance) if distance is not None else None,
    )


async def top_players(
    db: AsyncSession,
    metric: LeaderboardMetric,
    filters: LeaderboardFilter,
    limit: int = 20,
) -> list[LeaderboardRow]:
    """Первые limit игроков по выбранной метрике."""
    records = (await db.execute(_ordered(metric, filters).limit(limit))).all()
    return [_row(index, record) for index, record in enumerate(records, start=1)]


async def place_of(
    db: AsyncSession,
    metric: LeaderboardMetric,
    filters: LeaderboardFilter,
    user: User,
) -> LeaderboardRow | None:
    """
    Место конкретного игрока, если он вообще попадает в таблицу.

    Считается как «сколько игроков строго лучше» плюс один — так позиция не
    зависит от того, сколько строк запросили.
    """
    if not user.is_active:
        return None

    mine = (await db.execute(_aggregated(filters).having(User.id == user.id))).one_or_none()
    if mine is None:
        return None

    row = _row(0, mine)

    if metric is LeaderboardMetric.BEST:
        value, better_than = row.best_score, "best"
    elif metric is LeaderboardMetric.TOTAL:
        value, better_than = row.total_score, "total"
    else:
        if row.total_rounds < MIN_ROUNDS_FOR_ACCURACY or row.average_distance is None:
            return None
        value, better_than = row.average_distance, "miss"

    ranked = _ordered(metric, filters).subquery()
    column = ranked.c[better_than]
    condition = column < value if metric is LeaderboardMetric.ACCURACY else column > value

    better = select(func.count()).select_from(ranked).where(condition)
    rank = int((await db.execute(better)).scalar_one()) + 1

    return LeaderboardRow(
        rank=rank,
        user=row.user,
        games_played=row.games_played,
        total_rounds=row.total_rounds,
        best_score=row.best_score,
        total_score=row.total_score,
        average_distance=row.average_distance,
    )
