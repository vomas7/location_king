"""
Друзья.

Проверяется главное: добавляют по коду, а не по имени; чужих идентификаторов
в ответах нет; встречная заявка не заводит вторую связь; зачёт среди друзей
считает только их.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.models.user import User
from app.services.auth import create_token, register
from tests.helpers import play_through


@pytest.fixture
async def buddy(db: AsyncSession) -> User:
    user = await register(db, "buddy@example.com", "long enough password", "Приятель")
    await db.flush()
    return user


@pytest.fixture
def buddy_headers(buddy: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(buddy.id, 'access')}"}


async def test_everyone_gets_a_code(registered_user: User, buddy: User):
    """Код нужен всем: без него игрока не найти вовсе."""
    assert registered_user.friend_code
    assert buddy.friend_code
    assert registered_user.friend_code != buddy.friend_code


async def test_own_code_is_visible(client: AsyncClient, auth_headers: dict, registered_user: User):
    body = (await client.get("/api/friends", headers=auth_headers)).json()

    assert body["my_code"] == registered_user.friend_code
    assert body["friends"] == []


async def test_invite_and_accept(
    client: AsyncClient,
    auth_headers: dict,
    buddy_headers: dict,
    buddy: User,
):
    invited = await client.post(
        "/api/friends",
        json={"code": buddy.friend_code},
        headers=auth_headers,
    )
    assert invited.status_code == 201
    assert invited.json()["accepted"] is False

    # У приятеля она числится входящей и ждёт ответа
    incoming = (await client.get("/api/friends", headers=buddy_headers)).json()["friends"]
    assert len(incoming) == 1
    assert incoming[0]["incoming"] is True
    assert incoming[0]["display_name"] == "Игрок"

    accepted = await client.post(
        f"/api/friends/{incoming[0]['id']}/accept",
        headers=buddy_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True

    mine = (await client.get("/api/friends", headers=auth_headers)).json()["friends"]
    assert mine[0]["accepted"] is True
    assert mine[0]["incoming"] is False


async def test_friend_row_carries_no_stranger_id(
    client: AsyncClient,
    auth_headers: dict,
    buddy: User,
):
    """В строке друга — идентификатор связи, а не игрока."""
    body = (
        await client.post(
            "/api/friends",
            json={"code": buddy.friend_code},
            headers=auth_headers,
        )
    ).json()

    assert set(body) == {
        "id",
        "display_name",
        "avatar",
        "rating",
        "accepted",
        "incoming",
        "created_at",
    }


async def test_counter_invite_becomes_friendship(
    client: AsyncClient,
    auth_headers: dict,
    buddy_headers: dict,
    registered_user: User,
    buddy: User,
):
    """Позвали друг друга — договорились оба, спрашивать больше не о чем."""
    await client.post("/api/friends", json={"code": buddy.friend_code}, headers=auth_headers)

    back = await client.post(
        "/api/friends",
        json={"code": registered_user.friend_code},
        headers=buddy_headers,
    )

    assert back.status_code == 201
    assert back.json()["accepted"] is True

    mine = (await client.get("/api/friends", headers=auth_headers)).json()["friends"]
    assert len(mine) == 1, "вторая связь заводиться не должна"


async def test_inviting_twice_is_refused(
    client: AsyncClient,
    auth_headers: dict,
    buddy: User,
):
    await client.post("/api/friends", json={"code": buddy.friend_code}, headers=auth_headers)
    again = await client.post(
        "/api/friends",
        json={"code": buddy.friend_code},
        headers=auth_headers,
    )

    assert again.status_code == 409


async def test_own_code_is_refused(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: User,
):
    response = await client.post(
        "/api/friends",
        json={"code": registered_user.friend_code},
        headers=auth_headers,
    )

    assert response.status_code == 400


async def test_unknown_code_is_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.post("/api/friends", json={"code": "ZZZZZZ"}, headers=auth_headers)

    assert response.status_code == 404


async def test_only_the_addressee_accepts(
    client: AsyncClient,
    auth_headers: dict,
    buddy: User,
):
    invited = (
        await client.post(
            "/api/friends",
            json={"code": buddy.friend_code},
            headers=auth_headers,
        )
    ).json()

    response = await client.post(f"/api/friends/{invited['id']}/accept", headers=auth_headers)

    assert response.status_code == 409


async def test_stranger_cannot_touch_the_link(
    client: AsyncClient,
    auth_headers: dict,
    buddy_headers: dict,
    other_user_headers: dict,
    buddy: User,
):
    invited = (
        await client.post(
            "/api/friends",
            json={"code": buddy.friend_code},
            headers=auth_headers,
        )
    ).json()

    response = await client.delete(f"/api/friends/{invited['id']}", headers=other_user_headers)

    assert response.status_code == 404


async def test_link_can_be_removed(
    client: AsyncClient,
    auth_headers: dict,
    buddy: User,
):
    invited = (
        await client.post(
            "/api/friends",
            json={"code": buddy.friend_code},
            headers=auth_headers,
        )
    ).json()

    removed = await client.delete(f"/api/friends/{invited['id']}", headers=auth_headers)
    assert removed.status_code == 204

    assert (await client.get("/api/friends", headers=auth_headers)).json()["friends"] == []


# ─── Зачёт среди друзей ──────────────────────────────────────────────────


async def play_once(client: AsyncClient, headers: dict, zone: LocationZone) -> None:
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id},
        headers=headers,
    )
    await play_through(client, headers, started.json())


async def test_friends_leaderboard_counts_only_friends(
    client: AsyncClient,
    auth_headers: dict,
    buddy_headers: dict,
    other_user_headers: dict,
    buddy: User,
    zone: LocationZone,
):
    await play_once(client, auth_headers, zone)
    await play_once(client, buddy_headers, zone)
    await play_once(client, other_user_headers, zone)

    everyone = (await client.get("/api/leaderboard", headers=auth_headers)).json()
    assert len(everyone["entries"]) == 3

    # Пока друзей нет, в зачёте только сам игрок
    alone = (await client.get("/api/leaderboard?among_friends=true", headers=auth_headers)).json()
    assert [entry["display_name"] for entry in alone["entries"]] == ["Игрок"]
    assert alone["among_friends"] is True

    invited = (
        await client.post(
            "/api/friends",
            json={"code": buddy.friend_code},
            headers=auth_headers,
        )
    ).json()
    await client.post(f"/api/friends/{invited['id']}/accept", headers=buddy_headers)

    among = (await client.get("/api/leaderboard?among_friends=true", headers=auth_headers)).json()
    names = {entry["display_name"] for entry in among["entries"]}

    assert names == {"Игрок", "Приятель"}


async def test_pending_invite_does_not_join_the_standings(
    client: AsyncClient,
    auth_headers: dict,
    buddy_headers: dict,
    buddy: User,
    zone: LocationZone,
):
    """Неподтверждённая заявка — ещё не дружба."""
    await play_once(client, auth_headers, zone)
    await play_once(client, buddy_headers, zone)

    await client.post("/api/friends", json={"code": buddy.friend_code}, headers=auth_headers)

    among = (await client.get("/api/leaderboard?among_friends=true", headers=auth_headers)).json()

    assert [entry["display_name"] for entry in among["entries"]] == ["Игрок"]


async def test_friends_leaderboard_needs_a_name(client: AsyncClient):
    response = await client.get("/api/leaderboard?among_friends=true")

    assert response.status_code == 401
