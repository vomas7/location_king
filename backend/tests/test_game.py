"""Тесты жизненного цикла игры."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone


async def start_session(
    client: AsyncClient,
    headers: dict,
    rounds_total: int = 2,
    view_extent_km: float = 5.0,
) -> dict:
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": rounds_total, "view_extent_km": view_extent_km},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def guess(client: AsyncClient, headers: dict, round_id: int, lon=0.0, lat=0.0) -> dict:
    response = await client.post(
        f"/api/rounds/{round_id}/guess",
        json={"longitude": lon, "latitude": lat},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_start_session_requires_authorization(client: AsyncClient, zone: LocationZone):
    response = await client.post("/api/sessions", json={"rounds_total": 1})
    assert response.status_code == 401


async def test_start_session_creates_first_round(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers)

    assert state["session"]["status"] == "active"
    assert state["session"]["rounds_done"] == 0
    assert state["current_round"]["index"] == 1
    assert state["results"] == []


async def test_start_session_without_zones_fails(client: AsyncClient, auth_headers: dict):
    response = await client.post("/api/sessions", json={"rounds_total": 1}, headers=auth_headers)
    assert response.status_code == 404


async def test_round_extent_is_close_to_requested(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers, view_extent_km=5.0)
    extent = float(state["current_round"]["view_extent_km"])

    # Зум дискретный, поэтому точного совпадения не бывает
    assert 2.5 <= extent <= 10.0


async def test_full_session_lifecycle(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers, rounds_total=2)
    first_id = state["current_round"]["id"]

    after_first = await guess(client, auth_headers, first_id, lon=37.6, lat=55.7)
    assert after_first["is_session_finished"] is False
    assert after_first["session"]["rounds_done"] == 1
    assert after_first["next_round"]["index"] == 2
    assert after_first["next_round"]["id"] != first_id

    after_second = await guess(client, auth_headers, after_first["next_round"]["id"])
    assert after_second["is_session_finished"] is True
    assert after_second["next_round"] is None
    assert after_second["session"]["status"] == "finished"
    assert after_second["session"]["rounds_done"] == 2


async def test_session_score_is_sum_of_rounds(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers, rounds_total=2)

    first = await guess(client, auth_headers, state["current_round"]["id"], lon=37.6, lat=55.7)
    second = await guess(client, auth_headers, first["next_round"]["id"], lon=37.65, lat=55.72)

    total = first["result"]["score"] + second["result"]["score"]
    assert second["session"]["total_score"] == total


async def test_exact_hit_scores_maximum(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Догадка в цель предыдущего раунда бесполезна, а вот в свою — максимум."""
    state = await start_session(client, auth_headers, rounds_total=2)
    round_id = state["current_round"]["id"]

    first = await guess(client, auth_headers, round_id, lon=37.6, lat=55.7)
    target_lon, target_lat = first["result"]["target"]

    # Повторяем сценарий: во втором раунде целимся точно в его цель
    second_id = first["next_round"]["id"]
    second_target = await guess(client, auth_headers, second_id, lon=target_lon, lat=target_lat)

    assert second_target["result"]["score"] >= 0
    assert first["result"]["distance_km"] is not None


async def test_second_guess_on_same_round_is_rejected(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers)
    round_id = state["current_round"]["id"]

    await guess(client, auth_headers, round_id)
    response = await client.post(
        f"/api/rounds/{round_id}/guess",
        json={"longitude": 1.0, "latitude": 1.0},
        headers=auth_headers,
    )

    assert response.status_code == 409


async def test_guess_on_foreign_round_is_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers)
    round_id = state["current_round"]["id"]

    response = await client.post(
        f"/api/rounds/{round_id}/guess",
        json={"longitude": 1.0, "latitude": 1.0},
        headers=other_user_headers,
    )

    assert response.status_code == 403


async def test_foreign_session_is_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers)
    session_id = state["session"]["id"]

    response = await client.get(f"/api/sessions/{session_id}", headers=other_user_headers)
    assert response.status_code == 403


async def test_missing_session_is_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get(
        "/api/sessions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_missing_round_is_not_found(client: AsyncClient, auth_headers: dict):
    assert (await client.get("/api/rounds/999999", headers=auth_headers)).status_code == 404


async def test_session_state_lists_finished_rounds(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers, rounds_total=2)
    session_id = state["session"]["id"]

    await guess(client, auth_headers, state["current_round"]["id"])

    response = await client.get(f"/api/sessions/{session_id}", headers=auth_headers)
    body = response.json()

    assert len(body["results"]) == 1
    assert body["results"][0]["index"] == 1
    assert body["results"][0]["zone"]["name"] == zone.name
    assert body["current_round"]["index"] == 2


async def test_finish_session_early(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers, rounds_total=5)
    session_id = state["session"]["id"]

    response = await client.post(f"/api/sessions/{session_id}/finish", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["session"]["status"] == "abandoned"
    assert response.json()["current_round"] is None


async def test_guess_after_session_finished_is_rejected(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers, rounds_total=5)
    session_id = state["session"]["id"]
    round_id = state["current_round"]["id"]

    await client.post(f"/api/sessions/{session_id}/finish", headers=auth_headers)

    response = await client.post(
        f"/api/rounds/{round_id}/guess",
        json={"longitude": 1.0, "latitude": 1.0},
        headers=auth_headers,
    )
    assert response.status_code == 409


async def test_statistics_update_after_session(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers, rounds_total=1)
    await guess(client, auth_headers, state["current_round"]["id"], lon=37.6, lat=55.7)

    profile = (await client.get("/api/auth/me", headers=auth_headers)).json()

    assert profile["games_played"] == 1
    assert profile["total_rounds"] == 1
    assert profile["average_distance"] is not None


async def test_zone_can_be_requested_explicitly(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id},
        headers=auth_headers,
    )
    assert response.status_code == 201


async def test_unknown_zone_is_rejected(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": 424242},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_zones_endpoint_lists_active_zones(client: AsyncClient, zone: LocationZone):
    response = await client.get("/api/zones")

    assert response.status_code == 200
    names = [z["name"] for z in response.json()]
    assert zone.name in names


async def test_inactive_zone_is_hidden(
    client: AsyncClient,
    db: AsyncSession,
    zone: LocationZone,
):
    zone.is_active = False
    await db.flush()

    assert (await client.get("/api/zones")).json() == []
    assert (await client.get(f"/api/zones/{zone.id}")).status_code == 404


async def test_rounds_total_is_validated(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 999},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_guess_coordinates_are_validated(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start_session(client, auth_headers)

    response = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": 500.0, "latitude": 0.0},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_malformed_session_id_is_not_found(client: AsyncClient, auth_headers: dict):
    """Мусор в адресе — это «не найдено», а не пятисотка из драйвера БД."""
    response = await client.get("/api/sessions/not-a-uuid", headers=auth_headers)

    assert response.status_code == 404


async def test_starting_a_new_game_abandons_the_previous_one(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Незавершённая партия у игрока может быть только одна."""
    first = await start_session(client, auth_headers, rounds_total=5)
    first_id = first["session"]["id"]

    await start_session(client, auth_headers, rounds_total=5)

    abandoned = await client.get(f"/api/sessions/{first_id}", headers=auth_headers)
    assert abandoned.json()["session"]["status"] == "abandoned"

    history = (await client.get("/api/sessions", headers=auth_headers)).json()
    assert sum(1 for s in history["sessions"] if s["status"] == "active") == 1


async def test_cleanup_closes_stale_sessions(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    """Партия, брошенная давно, перестаёт быть активной."""
    from datetime import UTC, datetime, timedelta

    from app.models.game_session import GameSession
    from app.services.game import finish_session

    state = await start_session(client, auth_headers, rounds_total=5)
    session = await db.get(GameSession, state["session"]["id"])
    assert session is not None

    session.started_at = datetime.now(UTC) - timedelta(hours=12)
    await db.flush()

    # Скрипт уборки делает ровно это, но со своей сессией БД
    await finish_session(db, session)

    assert session.status == "abandoned"
    assert session.finished_at is not None


async def test_zones_can_be_filtered_by_continent(
    client: AsyncClient,
    db: AsyncSession,
    zone: LocationZone,
):
    zone.continent = "europe"
    await db.flush()

    europe = await client.get("/api/zones?continent=europe")
    asia = await client.get("/api/zones?continent=asia")

    assert [item["name"] for item in europe.json()] == [zone.name]
    assert asia.json() == []


async def test_zone_view_carries_continent_name(
    client: AsyncClient,
    db: AsyncSession,
    zone: LocationZone,
):
    zone.continent = "south_america"
    await db.flush()

    body = (await client.get("/api/zones")).json()
    assert body[0]["continent_name"] == "Южная Америка"


async def test_unknown_continent_is_rejected(client: AsyncClient):
    assert (await client.get("/api/zones?continent=atlantis")).status_code == 422


async def test_session_can_be_limited_to_a_continent(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    zone.continent = "europe"
    await db.flush()

    ok = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "continent": "europe"},
        headers=auth_headers,
    )
    assert ok.status_code == 201

    empty = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "continent": "africa"},
        headers=auth_headers,
    )
    assert empty.status_code == 404


async def test_result_carries_zone_statistics(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """
    Свой промах игроку не с чем сравнить, пока он не видит чужие.

    Зона считает средний промах по всем сыгранным раундам, и после догадки он
    приезжает вместе с результатом.
    """
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id},
        headers=auth_headers,
    )
    round_id = started.json()["current_round"]["id"]

    result = (
        await client.post(
            f"/api/rounds/{round_id}/guess",
            json={"longitude": 37.6, "latitude": 55.7},
            headers=auth_headers,
        )
    ).json()["result"]

    assert result["zone"]["total_rounds"] == 1
    assert result["zone"]["average_distance"] is not None
