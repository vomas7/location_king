"""
Время раунда.

Отдельный модуль, потому что срок нужен и обычной игре, и челленджу, а те
друг друга не импортируют. Все решения о времени принимает сервер: часы
игрока к делу не относятся.
"""

from datetime import UTC, datetime, timedelta

from app.models.game_session import GameSession
from app.models.round import Round

# Допуск на дорогу ответа до сервера: игрок, нажавший в последнюю секунду, не
# должен получать ноль из-за сети
ANSWER_GRACE_SECONDS = 3

# Из чего можно выбирать ограничение времени на раунд
ALLOWED_TIME_LIMITS = (30, 60, 120)


def deadline_for(session: GameSession) -> datetime | None:
    """До какого момента принимается ответ на новый раунд этой партии."""
    if session.time_limit_seconds is None:
        return None

    return datetime.now(UTC) + timedelta(seconds=session.time_limit_seconds)


def time_left_fraction(session: GameSession, round_obj: Round) -> float | None:
    """Какая доля отведённого времени осталась на момент ответа."""
    if session.time_limit_seconds is None or round_obj.deadline_at is None:
        return None

    left = (round_obj.deadline_at - datetime.now(UTC)).total_seconds()
    return left / session.time_limit_seconds


def is_late(round_obj: Round) -> bool:
    """Ответ пришёл после срока — с поправкой на дорогу до сервера."""
    if round_obj.deadline_at is None:
        return False

    return datetime.now(UTC) > round_obj.deadline_at + timedelta(seconds=ANSWER_GRACE_SECONDS)
