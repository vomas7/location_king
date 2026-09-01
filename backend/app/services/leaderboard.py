"""
Таблица лидеров.

Считается по завершённым партиям, а не по итоговым цифрам в профиле: зачёт
делится по условиям игры — уровню и месту, — а профиль знает только сумму за
всё время и разделить её обратно нельзя.

Партии, сыгранные до того, как условия начали запоминаться, попадают только в
общий зачёт: с каким уровнем их играли, теперь уже не выяснить.
"""

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RoundStatus, SessionStatus
from app.models.game_session import GameSession
from app.models.round import Round
from app.models.series import RoundSeries
from app.models.user import User

# Меньше этого числа раундов статистика по точности ничего не значит
MIN_ROUNDS_FOR_ACCURACY = 5

#: Какую долю максимума раунда надо взять, чтобы раунд считался метким.
#: Девять десятых — это попадание в считаные километры: место не просто
#: узнали, а нашли. Меткость намеренно считается иначе, чем точность: точность
#: это среднее, и один провальный раунд портит её целиком, а здесь каждый
#: удачный раунд остаётся в зачёте навсегда
SHARP_SHARE = 0.9


class LeaderboardMetric(StrEnum):
    """По чему ранжируем игроков."""

    BEST = "best"  # лучшая партия, очков за раунд
    TOTAL = "total"  # сумма очков за все партии
    ACCURACY = "accuracy"  # средний промах, меньше — лучше
    GAMES = "games"  # сколько партий доиграно
    SHARP = "sharp"  # сколько раундов взято почти в точку


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
    sharp_rounds: int


@dataclass(frozen=True)
class _Ranking:
    """
    Как считается место по одной метрике.

    Метрика встречается в двух видах: столбцом запроса, когда игроков
    выстраивают по порядку, и полем строки, когда у одного игрока спрашивают
    его цифру. Здесь оба вида названы рядом, чтобы они не разъезжались.
    """

    #: Имя столбца в запросе: по нему и сортируем, и считаем, сколько выше
    column: str

    #: Та же величина в готовой строке
    of_row: Callable[[LeaderboardRow], float | int | None]

    #: Меньше — лучше. Так устроен только промах
    ascending: bool = False

    #: Кого метрика вообще берёт в зачёт. Одно правило на двух языках: для
    #: запроса — условием, для готовой строки — проверкой, и разъехаться им
    #: нельзя, иначе игрок увидит место, которого нет в таблице
    gate: Callable[[Select], Select] = lambda stmt: stmt
    counts: Callable[[LeaderboardRow], bool] = lambda row: True


def _accuracy_counts(row: LeaderboardRow) -> bool:
    return row.total_rounds >= MIN_ROUNDS_FOR_ACCURACY and row.average_distance is not None


def _accuracy_gate(stmt: Select) -> Select:
    return stmt.having(
        func.sum(GameSession.rounds_done) >= MIN_ROUNDS_FOR_ACCURACY,
        func.avg(GameSession.average_distance).is_not(None),
    )


RANKINGS: dict[LeaderboardMetric, _Ranking] = {
    LeaderboardMetric.BEST: _Ranking("best", lambda row: row.best_score),
    LeaderboardMetric.TOTAL: _Ranking("total", lambda row: row.total_score),
    LeaderboardMetric.GAMES: _Ranking("games", lambda row: row.games_played),
    LeaderboardMetric.SHARP: _Ranking("sharp", lambda row: row.sharp_rounds),
    LeaderboardMetric.ACCURACY: _Ranking(
        "miss",
        lambda row: row.average_distance,
        ascending=True,
        gate=_accuracy_gate,
        counts=_accuracy_counts,
    ),
}


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
            _sharp_rounds(filters).label("sharp"),
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

    return _under(stmt, filters)


def _under(stmt: Select, filters: LeaderboardFilter) -> Select:
    """Дописать к запросу условия зачёта. Одни и те же на всех запросах."""
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


def _sharp_rounds(filters: LeaderboardFilter) -> Select:
    """
    Сколько раундов игрок взял почти в точку.

    Отдельным подзапросом, а не соединением с раундами: соединение размножило
    бы строки партий, и «сумма очков» вместе с «партиями» выросли бы во
    столько раз, сколько в партии раундов.
    """
    stmt = (
        select(func.count())
        .select_from(Round)
        .join(GameSession, GameSession.id == Round.session_id)
        .outerjoin(RoundSeries, GameSession.series_id == RoundSeries.id)
        .where(
            GameSession.user_id == User.id,
            GameSession.status == SessionStatus.FINISHED,
            Round.status != RoundStatus.ACTIVE,
            Round.score >= Round.max_score * SHARP_SHARE,
        )
    )

    return _under(stmt, filters).correlate(User).scalar_subquery()


def _ordered(metric: LeaderboardMetric, filters: LeaderboardFilter) -> Select:
    """
    Тот же запрос, отсортированный по выбранной метрике.

    Сортируем по имени столбца, а не по выражению: подзапрос меткости иначе
    попал бы в запрос дважды — в список столбцов и в ORDER BY.
    """
    ranking = RANKINGS[metric]
    stmt = ranking.gate(_aggregated(filters))
    direction = asc if ranking.ascending else desc

    return stmt.order_by(direction(ranking.column), User.id)


def _row(rank: int, record: tuple) -> LeaderboardRow:
    user, games, rounds, best, total, distance, sharp = record

    return LeaderboardRow(
        rank=rank,
        user=user,
        games_played=int(games),
        total_rounds=int(rounds),
        best_score=int(best),
        total_score=int(total),
        average_distance=float(distance) if distance is not None else None,
        sharp_rounds=int(sharp),
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
    ranking = RANKINGS[metric]
    if not ranking.counts(row):
        return None

    ranked = _ordered(metric, filters).subquery()
    column = ranked.c[ranking.column]
    value = ranking.of_row(row)
    condition = column < value if ranking.ascending else column > value

    better = select(func.count()).select_from(ranked).where(condition)
    rank = int((await db.execute(better)).scalar_one()) + 1

    return dataclasses.replace(row, rank=rank)
