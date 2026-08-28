"""Серии дней челленджа."""

from datetime import date, timedelta

import pytest

from app.utils.streak import current_and_best

TODAY = date(2026, 8, 28)


def days_ago(*offsets: int) -> list[date]:
    return [TODAY - timedelta(days=offset) for offset in offsets]


def test_no_games_no_streak():
    assert current_and_best([], TODAY) == (0, 0)


def test_single_day_today():
    assert current_and_best(days_ago(0), TODAY) == (1, 1)


def test_three_days_in_a_row():
    assert current_and_best(days_ago(0, 1, 2), TODAY) == (3, 3)


def test_yesterday_keeps_the_streak_alive():
    """Игрок ещё не садился сегодня — день у него впереди, серия жива."""
    assert current_and_best(days_ago(1, 2), TODAY) == (2, 2)


def test_gap_of_two_days_breaks_it():
    assert current_and_best(days_ago(2, 3, 4), TODAY) == (0, 3)


def test_best_survives_a_break():
    """Лучшая серия остаётся, даже когда текущая оборвалась."""
    current, best = current_and_best(days_ago(0, 5, 6, 7, 8), TODAY)

    assert (current, best) == (1, 4)


def test_order_and_repeats_do_not_matter():
    shuffled = days_ago(2, 0, 1, 0)

    assert current_and_best(shuffled, TODAY) == (3, 3)


@pytest.mark.parametrize("offsets", [(0,), (0, 1), (0, 1, 2, 3, 4, 5, 6)])
def test_current_never_exceeds_best(offsets: tuple[int, ...]):
    current, best = current_and_best(days_ago(*offsets), TODAY)

    assert current <= best
