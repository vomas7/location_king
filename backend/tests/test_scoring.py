"""Тесты подсчёта очков — единственной формулы в проекте."""

import pytest

from app.services.scoring import MAX_ROUND_SCORE, evaluate_guess, max_distance_km


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
    limit = max_distance_km(5.0)
    result = evaluate_guess(0.0, 0.0, 0.0, 0.0, view_extent_km=5.0)

    assert result.score == MAX_ROUND_SCORE
    assert score_at(limit + 1, 5.0) == 0
    assert score_at(limit * 100, 5.0) == 0


def test_score_is_zero_exactly_at_the_limit():
    assert score_at(max_distance_km(5.0), 5.0) == 0


def test_score_decreases_monotonically_with_distance():
    scores = [score_at(km) for km in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 10.0)]

    assert scores == sorted(scores, reverse=True)
    assert scores[0] == MAX_ROUND_SCORE
    assert scores[-1] == 0


def test_score_is_rounded_to_tens():
    for km in (0.3, 1.7, 3.3, 6.6):
        assert score_at(km) % 10 == 0


def test_bigger_view_extent_forgives_bigger_miss():
    """Один и тот же промах на крупной области стоит дешевле."""
    assert score_at(5.0, view_extent_km=50.0) > score_at(5.0, view_extent_km=5.0)


def test_accuracy_falls_from_hundred_to_zero():
    assert evaluate_guess(0.0, 0.0, 0.0, 0.0, 5.0).accuracy == 100.0

    far = evaluate_guess(10.0, 0.0, 0.0, 0.0, 5.0)
    assert far.accuracy == 0.0


def test_non_positive_extent_is_rejected():
    with pytest.raises(ValueError, match="view_extent_km"):
        evaluate_guess(0.0, 0.0, 0.0, 0.0, view_extent_km=0.0)


def test_score_never_exceeds_round_maximum():
    result = evaluate_guess(0.0, 0.0, 0.0, 0.0, view_extent_km=5.0, max_score=1000)
    assert result.score == 1000
