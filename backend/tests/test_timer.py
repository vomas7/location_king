"""Тесты режимов с ограничением времени."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.models.round import Round
from app.services.scoring import SLOWEST_ANSWER_FACTOR, evaluate_guess, time_factor


async def start_timed(client: AsyncClient, headers: dict, seconds: int | None = 60) -> dict:
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 2, "time_limit_seconds": seconds},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def expire(db: AsyncSession, round_id: int) -> None:
    """Отмотать срок раунда в прошлое."""
    round_obj = await db.get(Round, round_id)
    assert round_obj is not None
    round_obj.deadline_at = datetime.now(UTC) - timedelta(seconds=30)
    await db.flush()


# ── Множитель за скорость ────────────────────────────────────────────


def test_no_timer_means_no_penalty():
    assert time_factor(None) == 1.0


def test_instant_answer_keeps_all_points():
    assert time_factor(1.0) == 1.0


def test_answer_at_the_buzzer_keeps_the_floor():
    assert time_factor(0.0) == pytest.approx(SLOWEST_ANSWER_FACTOR)


def test_factor_does_not_leave_its_range():
    assert time_factor(5.0) == 1.0
    assert time_factor(-5.0) == pytest.approx(SLOWEST_ANSWER_FACTOR)


def test_slow_answer_scores_less_than_fast_one():
    fast = evaluate_guess(0.0, 0.0, 0.0, 0.0, view_extent_km=5.0, time_left_fraction=1.0)
    slow = evaluate_guess(0.0, 0.0, 0.0, 0.0, view_extent_km=5.0, time_left_fraction=0.0)

    assert fast.score > slow.score
    assert slow.score == pytest.approx(fast.score * SLOWEST_ANSWER_FACTOR, rel=0.01)


# ── Партия с таймером ────────────────────────────────────────────────


async def test_round_carries_a_deadline(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers, seconds=60)

    assert state["session"]["time_limit_seconds"] == 60
    assert state["current_round"]["deadline_at"] is not None


async def test_round_without_timer_has_no_deadline(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers, seconds=None)

    assert state["session"]["time_limit_seconds"] is None
    assert state["current_round"]["deadline_at"] is None


@pytest.mark.parametrize("seconds", [10, 45, 999])
async def test_arbitrary_time_limits_are_rejected(
    client: AsyncClient,
    auth_headers: dict,
    seconds: int,
):
    """Режимы должны быть сравнимы, поэтому значения выбираются из списка."""
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 2, "time_limit_seconds": seconds},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_late_guess_scores_zero(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers)
    round_id = state["current_round"]["id"]
    await expire(db, round_id)

    answer = await client.post(
        f"/api/rounds/{round_id}/guess",
        json={"longitude": 37.6, "latitude": 55.7},
        headers=auth_headers,
    )

    assert answer.status_code == 200
    assert answer.json()["result"]["status"] == "timed_out"
    assert answer.json()["result"]["score"] == 0
    assert answer.json()["next_round"] is not None


async def test_timeout_closes_the_round(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers)
    round_id = state["current_round"]["id"]
    await expire(db, round_id)

    response = await client.post(f"/api/rounds/{round_id}/timeout", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["score"] == 0
    assert body["result"]["guess"] is None
    assert body["session"]["rounds_done"] == 1


async def test_timeout_before_the_deadline_is_rejected(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Иначе это был бы бесплатный пропуск неудобного раунда."""
    state = await start_timed(client, auth_headers)

    response = await client.post(
        f"/api/rounds/{state['current_round']['id']}/timeout",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert "не вышло" in response.json()["detail"]


async def test_timeout_on_untimed_round_is_rejected(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers, seconds=None)

    response = await client.post(
        f"/api/rounds/{state['current_round']['id']}/timeout",
        headers=auth_headers,
    )

    assert response.status_code == 409


async def test_timeout_on_foreign_round_is_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers)

    response = await client.post(
        f"/api/rounds/{state['current_round']['id']}/timeout",
        headers=other_user_headers,
    )

    assert response.status_code == 403


async def test_timed_out_round_stays_in_history(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers)
    session_id = state["session"]["id"]
    await expire(db, state["current_round"]["id"])

    await client.post(f"/api/rounds/{state['current_round']['id']}/timeout", headers=auth_headers)

    history = (await client.get(f"/api/sessions/{session_id}", headers=auth_headers)).json()
    assert len(history["results"]) == 1
    assert history["results"][0]["status"] == "timed_out"
    assert history["results"][0]["target"] is not None


async def test_answer_time_is_recorded(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_timed(client, auth_headers)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": 37.6, "latitude": 55.7},
        headers=auth_headers,
    )

    assert float(answer.json()["result"]["answer_seconds"]) >= 0
