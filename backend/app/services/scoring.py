"""
Единственная реализация подсчёта расстояния и очков.

Правила игры:
  * шкала логарифмическая: важно не «на сколько километров», а «во сколько
    раз» игрок промахнулся мимо показанного участка;
  * очки кончаются на восьми тысячах километров — это уже другой континент;
  * результат округляется до десятков, чтобы счёт читался.

Раньше шкала была линейной и упиралась в две ширины кадра: при обычном кадре
в сорок километров промах на сто километров стоил ровно ноль — столько же,
сколько тычок в другое полушарие. Игрок, узнавший регион, но промахнувшийся
мимо города, получал ровно то же, что не узнавший ничего, и играть в это было
неинтересно.
"""

import math
from dataclasses import dataclass

from app.utils.geo import haversine_km

# Максимум очков за раунд
MAX_ROUND_SCORE = 5000

# Промах, начиная с которого раунд не стоит ничего. Восемь тысяч километров —
# это соседний континент, а не соседняя область: дальше различать нечего
SCORE_LIMIT_KM = 8000.0

# Какую долю кадра считать попаданием в точку. Десятая часть кадра — это то,
# что игрок физически видит на снимке одним взглядом; ближе к цели шкала уже
# не различает, и очки там почти максимальные
BULLSEYE_FRACTION = 0.1

# Форма шкалы. Единица дала бы слишком щедрый хвост — тычок за две тысячи
# километров стоил бы пятой части раунда; двойка, наоборот, съедает середину,
# где как раз и находится осмысленная догадка. Полтора — между ними
SCORE_SHAPE = 1.5

# Дальше этого от границы правильной страны ответ не стоит ничего
COUNTRY_MISS_LIMIT_KM = 2000

# Сколько максимум даёт неправильная страна. Соседняя страна — это уже
# осмысленный ответ, но не тот же самый: угадавший должен получить заметно
# больше того, кто промахнулся на границу
WRONG_COUNTRY_CEILING = 0.5

# Во сколько обходится подсказка: столько от максимума раунда она забирает.
# Треть — это заметно, но не разорительно: подсказка должна быть выбором, а не
# признанием поражения.
HINT_COST_FRACTION = 0.3

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


def score_share(distance_km: float, view_extent_km: float) -> float:
    """
    Какая доля максимума раунда причитается за такой промах, от нуля до единицы.

    Считается по тому, во сколько раз промах больше «яблочка» — десятой доли
    кадра, — а не по тому, сколько в нём километров. Логарифм здесь потому,
    что и сам игрок рассуждает в кратностях: промахнуться на квартал, на
    город, на область и на континент — это четыре разных ответа, и расстояние
    между ними каждый раз больше на порядок, а не на постоянную величину.
    """
    if view_extent_km <= 0:
        raise ValueError("view_extent_km должен быть больше нуля")

    if distance_km >= SCORE_LIMIT_KM:
        return 0.0

    bullseye = view_extent_km * BULLSEYE_FRACTION
    scale = math.log1p(SCORE_LIMIT_KM / bullseye)
    missed = math.log1p(max(distance_km, 0.0) / bullseye) / scale

    return max(1.0 - missed, 0.0) ** SCORE_SHAPE


def score_after_hint(max_score: int) -> int:
    """Максимум раунда после взятой подсказки."""
    return int(max_score * (1 - HINT_COST_FRACTION)) // 10 * 10


def country_score(
    guessed_right: bool,
    distance_to_country_km: float,
    max_score: int = MAX_ROUND_SCORE,
) -> int:
    """
    Очки за ответ страной.

    Угадал — весь максимум. Не угадал — не больше половины, и тем меньше, чем
    дальше точка от границы правильной страны: ткнуть в соседнюю страну и
    ткнуть в другое полушарие — разные ошибки.
    """
    if guessed_right:
        return max_score

    ratio = min(max(distance_to_country_km, 0.0) / COUNTRY_MISS_LIMIT_KM, 1.0)
    return int(max_score * WRONG_COUNTRY_CEILING * (1 - ratio) ** 2) // 10 * 10


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
    share = score_share(distance, view_extent_km)

    score = int(max_score * share * time_factor(time_left_fraction)) // 10 * 10

    # Точность — про саму догадку, поэтому таймер и подсказку она не
    # учитывает: ответ на последней секунде не становится менее точным
    accuracy = round(share * 100, 2)

    return GuessResult(distance_km=round(distance, 3), score=score, accuracy=accuracy)
