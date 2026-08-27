"""Тесты комнат мультиплеера."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.models.user import User
from app.services import series as series_service
from tests.helpers import play_through


async def create_match(client: AsyncClient, headers: dict[str, str], **settings) -> dict:
    """Создать комнату и вернуть её представление."""
    response = await client.post(
        "/api/matches", json={"rounds_total": 2} | settings, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_host_creates_room_and_gets_code(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: User,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers)

    assert len(room["code"]) == 6
    assert room["status"] == "open"
    assert room["is_host"] is True
    assert room["host_name"] == registered_user.display_name
    assert room["rounds_total"] == 2
    assert room["players"] == 0
    assert room["my_session"] is None
    assert room["standings"] == []


async def test_room_requires_authorization(client: AsyncClient):
    assert (await client.post("/api/matches", json={})).status_code == 401


async def test_unknown_code_is_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/matches/ZZZZZZ", headers=auth_headers)

    assert response.status_code == 404


async def test_code_is_case_insensitive(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers)

    response = await client.get(f"/api/matches/{room['code'].lower()}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["code"] == room["code"]


async def test_players_get_the_same_rounds(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    """Комната на то и комната, что все играют одну серию."""
    room = await create_match(client, auth_headers)

    host = await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)
    guest = await client.post(f"/api/matches/{room['code']}/join", headers=other_user_headers)

    assert host.status_code == 201, host.text
    assert guest.status_code == 201, guest.text

    host_round = await db.get(Round, host.json()["current_round"]["id"])
    guest_round = await db.get(Round, guest.json()["current_round"]["id"])
    assert host_round is not None and guest_round is not None

    assert host_round.id != guest_round.id
    assert (host_round.tile_zoom, host_round.tile_x, host_round.tile_y) == (
        guest_round.tile_zoom,
        guest_round.tile_x,
        guest_round.tile_y,
    )


async def test_active_round_hides_the_target(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers)
    joined = await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)

    assert "target" not in joined.text
    assert zone.name not in joined.text


async def test_second_join_is_rejected(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Иначе можно было бы переигрывать серию, пока не выпадет удачный счёт."""
    room = await create_match(client, auth_headers)
    await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)

    again = await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)

    assert again.status_code == 409
    assert "уже играл" in again.json()["detail"]


async def test_join_closes_the_previous_game(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    ordinary = await client.post("/api/sessions", json={"rounds_total": 5}, headers=auth_headers)
    ordinary_id = ordinary.json()["session"]["id"]

    room = await create_match(client, auth_headers)
    await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)

    state = (await client.get(f"/api/sessions/{ordinary_id}", headers=auth_headers)).json()
    assert state["session"]["status"] == "abandoned"


async def test_closed_room_does_not_accept_players(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers)

    closed = await client.post(f"/api/matches/{room['code']}/close", headers=auth_headers)
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    late = await client.post(f"/api/matches/{room['code']}/join", headers=other_user_headers)
    assert late.status_code == 409
    assert "закрыт" in late.json()["detail"]


async def test_only_host_can_close_the_room(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers)

    response = await client.post(f"/api/matches/{room['code']}/close", headers=other_user_headers)

    assert response.status_code == 403
    assert (await client.get(f"/api/matches/{room['code']}", headers=auth_headers)).json()[
        "status"
    ] == "open"


async def test_standings_put_finished_players_first(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    other_user: User,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers)

    await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)
    guest = await client.post(f"/api/matches/{room['code']}/join", headers=other_user_headers)
    await play_through(client, other_user_headers, guest.json())

    table = (await client.get(f"/api/matches/{room['code']}", headers=auth_headers)).json()

    assert table["players"] == 2
    assert [row["rank"] for row in table["standings"]] == [1, 2]

    winner, waiting = table["standings"]
    assert winner["display_name"] == other_user.display_name
    assert winner["is_finished"] is True
    assert winner["is_you"] is False

    assert waiting["is_finished"] is False
    assert waiting["is_you"] is True
    assert waiting["rounds_done"] == 0


async def test_standings_never_expose_identifiers(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Клиенту хватает флага «это ты»: чужие идентификаторы ему не нужны."""
    room = await create_match(client, auth_headers)
    await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)

    row = (await client.get(f"/api/matches/{room['code']}", headers=auth_headers)).json()[
        "standings"
    ][0]

    assert "user_id" not in row
    assert "id" not in row


async def test_my_session_lets_the_player_return(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers)
    joined = await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)

    view = (await client.get(f"/api/matches/{room['code']}", headers=auth_headers)).json()

    assert view["my_session"]["id"] == joined.json()["session"]["id"]
    assert view["my_session"]["rounds_total"] == 2


async def test_room_settings_reach_the_rounds(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    room = await create_match(client, auth_headers, rounds_total=3, time_limit_seconds=60)

    assert room["time_limit_seconds"] == 60

    joined = await client.post(f"/api/matches/{room['code']}/join", headers=auth_headers)
    body = joined.json()

    assert body["session"]["rounds_total"] == 3
    assert body["session"]["time_limit_seconds"] == 60
    assert body["current_round"]["deadline_at"] is not None


async def test_host_sees_his_rooms(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    mine = await create_match(client, auth_headers)
    theirs = await create_match(client, other_user_headers)

    await client.post(f"/api/matches/{mine['code']}/join", headers=other_user_headers)

    listed = (await client.get("/api/matches/mine", headers=auth_headers)).json()["matches"]

    assert [room["code"] for room in listed] == [mine["code"]]
    assert listed[0]["players"] == 1
    assert theirs["code"] not in [room["code"] for room in listed]


async def test_too_long_series_is_rejected(db: AsyncSession, zone: LocationZone):
    """Серия собирается целиком в одном запросе, поэтому длина ограничена."""
    with pytest.raises(ConflictError):
        await series_service.create(db, series_service.MAX_ROUNDS + 1, view_extent_km=5.0)


async def test_rounds_total_is_validated_by_the_schema(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/matches",
        json={"rounds_total": series_service.MAX_ROUNDS + 1},
        headers=auth_headers,
    )

    assert response.status_code == 422
