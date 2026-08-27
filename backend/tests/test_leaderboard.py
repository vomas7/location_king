"""Тесты таблицы лидеров и истории партий."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.models.user import User
from app.services.auth import create_token, register


async def make_player(
    db: AsyncSession,
    email: str,
    *,
    best_score: int,
    total_score: int,
    games: int = 3,
    rounds: int = 15,
    average_distance: float | None = 10.0,
) -> User:
    """Игрок с уже посчитанной статистикой."""
    user = await register(db, email, "password for tests", email.split("@")[0])
    user.best_score = best_score
    user.total_score = total_score
    user.games_played = games
    user.total_rounds = rounds
    user.average_distance = average_distance
    await db.flush()
    return user


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(user.id, 'access')}"}


async def test_leaderboard_is_open_without_authorization(client: AsyncClient):
    response = await client.get("/api/leaderboard")

    assert response.status_code == 200
    assert response.json()["me"] is None


async def test_leaderboard_ranks_by_best_game(client: AsyncClient, db: AsyncSession):
    await make_player(db, "silver@example.com", best_score=3000, total_score=9000)
    await make_player(db, "gold@example.com", best_score=4800, total_score=5000)
    await make_player(db, "bronze@example.com", best_score=1000, total_score=1000)

    entries = (await client.get("/api/leaderboard?metric=best")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["gold", "silver", "bronze"]
    assert [e["rank"] for e in entries] == [1, 2, 3]


async def test_leaderboard_ranks_by_total_score(client: AsyncClient, db: AsyncSession):
    await make_player(db, "silver@example.com", best_score=3000, total_score=9000)
    await make_player(db, "gold@example.com", best_score=4800, total_score=5000)

    entries = (await client.get("/api/leaderboard?metric=total")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["silver", "gold"]


async def test_leaderboard_by_accuracy_puts_smallest_miss_first(
    client: AsyncClient,
    db: AsyncSession,
):
    await make_player(db, "far@example.com", best_score=1, total_score=1, average_distance=500.0)
    await make_player(db, "near@example.com", best_score=1, total_score=1, average_distance=2.5)

    entries = (await client.get("/api/leaderboard?metric=accuracy")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["near", "far"]


async def test_accuracy_ranking_ignores_players_with_too_few_rounds(
    client: AsyncClient,
    db: AsyncSession,
):
    await make_player(db, "rookie@example.com", best_score=1, total_score=1, rounds=2)
    await make_player(db, "veteran@example.com", best_score=1, total_score=1, rounds=50)

    entries = (await client.get("/api/leaderboard?metric=accuracy")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["veteran"]


async def test_guests_are_not_listed(client: AsyncClient, db: AsyncSession, guest: dict):
    guest_user = await db.get(User, guest["user"]["id"])
    guest_user.games_played = 10
    guest_user.best_score = 5000
    await db.flush()

    entries = (await client.get("/api/leaderboard")).json()["entries"]

    assert entries == []


async def test_players_without_games_are_not_listed(client: AsyncClient, registered_user: User):
    assert (await client.get("/api/leaderboard")).json()["entries"] == []


async def test_own_place_is_returned_even_outside_the_top(
    client: AsyncClient,
    db: AsyncSession,
):
    for index in range(5):
        await make_player(
            db,
            f"top{index}@example.com",
            best_score=5000 - index,
            total_score=1000,
        )
    outsider = await make_player(db, "me@example.com", best_score=10, total_score=10)

    body = (await client.get("/api/leaderboard?limit=3", headers=headers_for(outsider))).json()

    assert len(body["entries"]) == 3
    assert body["me"]["display_name"] == "me"
    assert body["me"]["rank"] == 6


async def test_guest_has_no_place(client: AsyncClient, auth_headers: dict):
    body = (await client.get("/api/leaderboard", headers=auth_headers)).json()
    assert body["me"] is None


async def test_invalid_metric_is_rejected(client: AsyncClient):
    assert (await client.get("/api/leaderboard?metric=nonsense")).status_code == 422


@pytest.mark.parametrize("limit", [0, 101])
async def test_limit_is_validated(client: AsyncClient, limit: int):
    assert (await client.get(f"/api/leaderboard?limit={limit}")).status_code == 422


# ── История партий ───────────────────────────────────────────────────


async def test_history_requires_authorization(client: AsyncClient):
    assert (await client.get("/api/sessions")).status_code == 401


async def test_history_is_empty_for_new_player(client: AsyncClient, auth_headers: dict):
    body = (await client.get("/api/sessions", headers=auth_headers)).json()

    assert body == {"sessions": [], "total": 0}


async def test_history_lists_played_sessions(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    for _ in range(2):
        state = await client.post(
            "/api/sessions",
            json={"rounds_total": 1},
            headers=auth_headers,
        )
        round_id = state.json()["current_round"]["id"]
        await client.post(
            f"/api/rounds/{round_id}/guess",
            json={"longitude": 37.6, "latitude": 55.7},
            headers=auth_headers,
        )

    body = (await client.get("/api/sessions", headers=auth_headers)).json()

    assert body["total"] == 2
    assert all(session["status"] == "finished" for session in body["sessions"])


async def test_history_does_not_show_other_players_sessions(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    await client.post("/api/sessions", json={"rounds_total": 1}, headers=auth_headers)

    body = (await client.get("/api/sessions", headers=other_user_headers)).json()
    assert body["total"] == 0


# ── Продолжение партии ───────────────────────────────────────────────


async def test_current_session_is_null_when_nothing_started(
    client: AsyncClient,
    auth_headers: dict,
):
    """Отсутствие партии — обычное состояние, а не ошибка."""
    response = await client.get("/api/sessions/current", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() is None


async def test_current_session_returns_unfinished_game(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 3},
        headers=auth_headers,
    )
    session_id = started.json()["session"]["id"]

    body = (await client.get("/api/sessions/current", headers=auth_headers)).json()

    assert body["session"]["id"] == session_id
    assert body["current_round"]["index"] == 1


async def test_current_session_is_gone_after_finish(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 1},
        headers=auth_headers,
    )
    session_id = started.json()["session"]["id"]
    await client.post(f"/api/sessions/{session_id}/finish", headers=auth_headers)

    assert (await client.get("/api/sessions/current", headers=auth_headers)).json() is None


async def test_current_session_carries_no_target_coordinates(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    await client.post("/api/sessions", json={"rounds_total": 3}, headers=auth_headers)

    body = (await client.get("/api/sessions/current", headers=auth_headers)).text

    assert "target" not in body
    assert zone.name not in body


async def test_current_session_requires_authorization(client: AsyncClient):
    assert (await client.get("/api/sessions/current")).status_code == 401
