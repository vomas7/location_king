"""
Единственная реализация подсчёта расстояния и очков.

Правила игры:
  * очки начисляются, пока догадка не дальше двух размеров показанной области;
  * зависимость квадратичная — промах на четверть допустимого расстояния
    стоит почти половины очков;
  * результат округляется до десятков, чтобы счёт читался.
"""

from dataclasses import dataclass

from app.utils.geo import haversine_km

# Максимум очков за раунд
MAX_ROUND_SCORE = 5000

# Во сколько раз дальше размера области можно промахнуться, ещё получая очки
MAX_DISTANCE_FACTOR = 2

# Доля очков, которая остаётся у того, кто ответил на последней секунде.
# Скорость не добавляет очков сверх максимума, а медлительность их отнимает:
# иначе результаты партий с таймером и без были бы несравнимы.
SLOWEST_ANSWER_FACTOR = 0.8


@dataclass(frozen=True)
class GuessResult:
    """Результат оценки одной догадки."""

    distance_km: float
    score: int
    accuracy: float


def max_distance_km(view_extent_km: float) -> float:
    """Расстояние, начиная с которого догадка не приносит очков."""
    return view_extent_km * MAX_DISTANCE_FACTOR


def time_factor(time_left_fraction: float | None) -> float:
    """
    Множитель очков за скорость ответа.

    Без таймера множитель единица. С таймером он падает от единицы до
    SLOWEST_ANSWER_FACTOR по мере того, как заканчивается время.
    """
    if time_left_fraction is None:
        return 1.0

    left = min(max(time_left_fraction, 0.0), 1.0)
    return SLOWEST_ANSWER_FACTOR + (1.0 - SLOWEST_ANSWER_FACTOR) * left


def evaluate_guess(
    guess_lon: float,
    guess_lat: float,
    target_lon: float,
    target_lat: float,
    view_extent_km: float,
    max_score: int = MAX_ROUND_SCORE,
    time_left_fraction: float | None = None,
) -> GuessResult:
    """Оценить догадку: расстояние до цели, очки и точность в процентах."""
    if view_extent_km <= 0:
        raise ValueError("view_extent_km должен быть больше нуля")

    distance = haversine_km(guess_lon, guess_lat, target_lon, target_lat)
    limit = max_distance_km(view_extent_km)
    ratio = min(distance / limit, 1.0)

    base = max_score * (1 - ratio) ** 2
    score = int(base * time_factor(time_left_fraction)) // 10 * 10
    accuracy = round((1 - ratio) * 100, 2)

    return GuessResult(distance_km=round(distance, 3), score=score, accuracy=accuracy)
