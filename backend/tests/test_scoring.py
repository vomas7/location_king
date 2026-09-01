"""Тесты подсчёта очков — единственной формулы в проекте."""

import pytest

from app.services.scoring import MAX_ROUND_SCORE, SCORE_LIMIT_KM, evaluate_guess


def score_at(distance_km: float, view_extent_km: float = 5.0) -> int:
    """Очки за догадку, отстоящую от цели строго на восток на заданное расстояние."""
    # На экваторе 1 градус долготы ≈ 111.195 км
    target_lon = 0.0
    guess_lon = distance_km / 111.19492664455873

    return evaluate_guess(guess_lon, 0.0, target_lon, 0.0, view_extent_km).score


def test_exact_hit_gives_maximum_score():
    result = evaluate_guess(37.6, 55.75, 37.6, 55.75, view_extent_km=5.0)

    assert result.distance_km == 0.0
    assert result.score == MAX_ROUND_SCORE
    assert result.accuracy == 100.0


def test_guess_beyond_limit_gives_zero():
    assert score_at(SCORE_LIMIT_KM, 5.0) == 0
    assert score_at(SCORE_LIMIT_KM + 1, 5.0) == 0
    assert score_at(SCORE_LIMIT_KM * 2, 5.0) == 0


def test_limit_does_not_depend_on_the_frame():
    """Ноль наступает там, где догадка перестаёт быть догадкой, а не у края кадра."""
    for extent in (5.0, 40.0, 300.0):
        assert score_at(SCORE_LIMIT_KM, extent) == 0


def test_plausible_miss_is_not_a_zero():
    """
    Главная жалоба на прежнюю шкалу: при обычном кадре в сорок километров
    промах на сотню стоил ровно столько же, сколько тычок в другое полушарие.
    """
    near = score_at(100.0, view_extent_km=40.0)
    across_the_world = score_at(9000.0, view_extent_km=40.0)

    assert across_the_world == 0
    assert near > MAX_ROUND_SCORE * 0.3


def test_precision_still_pays_more_than_a_lucky_region():
    """Узнать место и узнать область — разные ответы, и очки за них разные."""
    assert score_at(1.0, 40.0) > score_at(25.0, 40.0) > score_at(200.0, 40.0)
    assert score_at(1.0, 40.0) > 2 * score_at(200.0, 40.0)


def test_score_decreases_monotonically_with_distance():
    scores = [score_at(km) for km in (0.0, 0.5, 1.0, 10.0, 100.0, 1000.0, 9000.0)]

    assert scores == sorted(scores, reverse=True)
    assert scores[0] == MAX_ROUND_SCORE
    assert scores[-1] == 0


def test_score_is_rounded_to_tens():
    for km in (0.3, 1.7, 3.3, 6.6, 250.0):
        assert score_at(km) % 10 == 0


def test_bigger_view_extent_forgives_bigger_miss():
    """Один и тот же промах на крупной области стоит дешевле."""
    assert score_at(5.0, view_extent_km=50.0) > score_at(5.0, view_extent_km=5.0)


def test_accuracy_falls_from_hundred_to_zero():
    assert evaluate_guess(0.0, 0.0, 0.0, 0.0, 5.0).accuracy == 100.0

    far = evaluate_guess(SCORE_LIMIT_KM / 111.19492664455873, 0.0, 0.0, 0.0, 5.0)
    assert far.accuracy == 0.0


def test_accuracy_ignores_the_timer():
    """Ответ на последней секунде не становится менее точным — только дешевле."""
    quick = evaluate_guess(0.1, 0.0, 0.0, 0.0, 5.0, time_left_fraction=1.0)
    slow = evaluate_guess(0.1, 0.0, 0.0, 0.0, 5.0, time_left_fraction=0.0)

    assert quick.accuracy == slow.accuracy
    assert quick.score > slow.score


def test_non_positive_extent_is_rejected():
    with pytest.raises(ValueError, match="view_extent_km"):
        evaluate_guess(0.0, 0.0, 0.0, 0.0, view_extent_km=0.0)


def test_score_never_exceeds_round_maximum():
    result = evaluate_guess(0.0, 0.0, 0.0, 0.0, view_extent_km=5.0, max_score=1000)
    assert result.score == 1000
