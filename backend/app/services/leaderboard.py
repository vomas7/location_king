"""
Таблица лидеров.

Статистика уже посчитана в таблице users сервисом игры, поэтому здесь только
сортировка и позиция игрока. Гости в таблицу не попадают: их учётки одноразовые
и засоряли бы её именами вида «Гость 1A2B».
"""

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

# Меньше этого числа раундов статистика по точности ничего не значит
MIN_ROUNDS_FOR_ACCURACY = 5


class LeaderboardMetric(StrEnum):
    """По чему ранжируем игроков."""

    BEST = "best"  # лучшая партия
    TOTAL = "total"  # сумма очков за все партии
    ACCURACY = "accuracy"  # средний промах, меньше — лучше


@dataclass(frozen=True)
class LeaderboardRow:
    """Строка таблицы вместе с занятым местом."""

    rank: int
    user: User


def _base_query(metric: LeaderboardMetric) -> Select:
    """Запрос игроков, отсортированный по выбранной метрике."""
    query = select(User).where(
        User.is_active.is_(True),
        User.is_guest.is_(False),
        User.games_played > 0,
    )

    if metric is LeaderboardMetric.BEST:
        return query.order_by(User.best_score.desc(), User.id)

    if metric is LeaderboardMetric.TOTAL:
        return query.order_by(User.total_score.desc(), User.id)

    return query.where(
        User.total_rounds >= MIN_ROUNDS_FOR_ACCURACY,
        User.average_distance.is_not(None),
    ).order_by(User.average_distance.asc(), User.id)


async def top_players(
    db: AsyncSession,
    metric: LeaderboardMetric,
    limit: int = 20,
) -> list[LeaderboardRow]:
    """Первые limit игроков по выбранной метрике."""
    users = (await db.execute(_base_query(metric).limit(limit))).scalars().all()
    return [LeaderboardRow(rank=index, user=user) for index, user in enumerate(users, start=1)]


async def place_of(
    db: AsyncSession, metric: LeaderboardMetric, user: User
) -> LeaderboardRow | None:
    """
    Место конкретного игрока, если он вообще попадает в таблицу.

    Считается как «сколько игроков строго лучше» плюс один — так позиция не
    зависит от размера выборки.
    """
    if user.is_guest or not user.is_active or user.games_played == 0:
        return None

    ranked = _base_query(metric).subquery()
    better = select(func.count()).select_from(ranked)

    if metric is LeaderboardMetric.BEST:
        better = better.where(ranked.c.best_score > user.best_score)
    elif metric is LeaderboardMetric.TOTAL:
        better = better.where(ranked.c.total_score > user.total_score)
    else:
        if user.total_rounds < MIN_ROUNDS_FOR_ACCURACY or user.average_distance is None:
            return None
        better = better.where(ranked.c.average_distance < user.average_distance)

    return LeaderboardRow(rank=int((await db.execute(better)).scalar_one()) + 1, user=user)
