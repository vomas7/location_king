"""
Аватарка игрока.

Файлов здесь нет намеренно: аватарка — это два числа, а узор по ним рисует
клиент. Проверяется, что числа осмысленные, что их можно поменять и что они
доезжают туда, где игрока видят другие.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.models.user import User
from app.services.auth import register
from app.utils import avatar
from tests.helpers import play_through


def test_neighbours_get_different_avatars():
    """Одинаковая заглушка у всех означала бы, что аватарки нет."""
    seen = {avatar.default_for(user_id) for user_id in range(1, avatar.SHAPES + 1)}

    assert len(seen) == avatar.SHAPES


def test_every_default_avatar_exists():
    for user_id in range(1, 200):
        shape, color = avatar.default_for(user_id)
        assert avatar.is_known(shape, color), user_id


def test_unknown_avatar_is_rejected():
    assert not avatar.is_known(avatar.SHAPES, 0)
    assert not avatar.is_known(0, -1)


async def test_registration_hands_out_an_avatar(db: AsyncSession):
    user = await register(db, "fresh@example.com", "long enough password", "Новичок")

    assert avatar.is_known(user.avatar_shape, user.avatar_color)
    assert (user.avatar_shape, user.avatar_color) == avatar.default_for(user.id)


async def test_profile_carries_the_avatar(client: AsyncClient, auth_headers: dict):
    body = (await client.get("/api/auth/me", headers=auth_headers)).json()

    assert set(body["avatar"]) == {"shape", "color"}
    assert avatar.is_known(body["avatar"]["shape"], body["avatar"]["color"])


async def test_avatar_can_be_changed(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/auth/me",
        json={"avatar_shape": 3, "avatar_color": 4},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["avatar"] == {"shape": 3, "color": 4}


async def test_name_and_avatar_change_together(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/auth/me",
        json={"display_name": "Штурман", "avatar_shape": 1, "avatar_color": 2},
        headers=auth_headers,
    )

    body = response.json()
    assert body["display_name"] == "Штурман"
    assert body["avatar"] == {"shape": 1, "color": 2}


async def test_avatar_that_does_not_exist_is_refused(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/api/auth/me",
        json={"avatar_shape": 90, "avatar_color": 0},
        headers=auth_headers,
    )

    assert response.status_code == 400


async def test_empty_change_is_an_error(client: AsyncClient, auth_headers: dict):
    """Пустой запрос — ошибка клиента, а не вежливое «ничего не делай»."""
    response = await client.patch("/api/auth/me", json={}, headers=auth_headers)

    assert response.status_code == 422


async def test_leaderboard_shows_avatars(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id},
        headers=auth_headers,
    )
    await play_through(client, auth_headers, started.json())

    entries = (await client.get("/api/leaderboard")).json()["entries"]

    assert entries
    assert avatar.is_known(entries[0]["avatar"]["shape"], entries[0]["avatar"]["color"])


async def test_room_standings_show_avatars(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: User,
    zone: LocationZone,
):
    """
    В таблице комнаты чужих идентификаторов нет — и не будет.

    Поэтому аватарку клиент не выводит из идентификатора сам: она приезжает
    вместе со строкой.
    """
    created = await client.post(
        "/api/matches",
        json={"rounds_total": 1, "view_extent_km": 15.0},
        headers=auth_headers,
    )
    code = created.json()["code"]
    await client.post(f"/api/matches/{code}/join", headers=auth_headers)

    room = (await client.get(f"/api/matches/{code}", headers=auth_headers)).json()

    assert room["standings"]
    assert "user_id" not in room["standings"][0]
    assert room["standings"][0]["avatar"] == {
        "shape": registered_user.avatar_shape,
        "color": registered_user.avatar_color,
    }
