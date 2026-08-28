"""
Серии дней: сколько дней подряд игрок доходил до конца челленджа.

Чистые функции без обращения к базе — их проще проверить на краях, а краёв
здесь много: пропущенный день, единственный день, серия, идущая прямо сейчас.
"""

from collections.abc import Iterable
from datetime import date, timedelta
from itertools import pairwise

DAY = timedelta(days=1)


def current_and_best(days: Iterable[date], today: date) -> tuple[int, int]:
    """
    Текущая и лучшая серия по дням, в которые игрок закончил челлендж.

    Серия считается живой, пока игрок может её продолжить: сыграл сегодня —
    очевидно, сыграл вчера и ещё не садился сегодня — тоже, у него весь день
    впереди. Обрыв на позавчера обнуляет счётчик: обещать несуществующую
    серию хуже, чем не показывать её вовсе.

    Повторы и порядок значения не имеют: считаем по множеству дат.
    """
    played = sorted(set(days))
    if not played:
        return 0, 0

    best = run = 1
    for previous, day in pairwise(played):
        run = run + 1 if day - previous == DAY else 1
        best = max(best, run)

    last = played[-1]
    current = run if last in (today, today - DAY) else 0

    return current, best
