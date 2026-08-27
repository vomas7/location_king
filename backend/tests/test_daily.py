"""Тесты челленджа дня."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily import DailyChallenge
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.models.series import SeriesRound
from app.services import daily as daily_service
from tests.helpers import play_through


async def test_today_is_available_before_playing(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    response = await client.get("/api/challenge/today", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["day"] == daily_service.today().isoformat()
    assert body["rounds_total"] == daily_service.ROUNDS_TOTAL
    assert body["my_session"] is None
    assert body["results"] == []


async def test_today_requires_authorization(client: AsyncClient):
    assert (await client.get("/api/challenge/today")).status_code == 401


async def test_challenge_is_built_once_and_shared(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    """Двое игроков получают одни и те же раунды."""
    first = await client.post("/api/challenge/today/start", headers=auth_headers)
    second = await client.post("/api/challenge/today/start", headers=other_user_headers)

    assert first.status_code == 201
    assert second.status_code == 201

    challenges = (await db.execute(select(DailyChallenge))).scalars().all()
    assert len(challenges) == 1

    rounds = (await db.execute(select(SeriesRound).order_by(SeriesRound.position))).scalars().all()
    assert [item.position for item in rounds] == [1, 2, 3, 4, 5]

    # Раунды игроков скопированы из одной заготовки
    first_round_id = first.json()["current_round"]["id"]
    second_round_id = second.json()["current_round"]["id"]
    assert first_round_id != second_round_id

    mine = await db.get(Round, first_round_id)
    theirs = await db.get(Round, second_round_id)
    assert mine is not None and theirs is not None
    assert (mine.tile_zoom, mine.tile_x, mine.tile_y) == (
        theirs.tile_zoom,
        theirs.tile_x,
        theirs.tile_y,
    )


async def test_challenge_cannot_be_played_twice(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    assert (
        await client.post("/api/challenge/today/start", headers=auth_headers)
    ).status_code == 201

    second = await client.post("/api/challenge/today/start", headers=auth_headers)
    assert second.status_code == 409
    assert "уже сыгран" in second.json()["detail"]


async def test_challenge_rounds_follow_the_template_order(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    started = await client.post("/api/challenge/today/start", headers=auth_headers)
    finished = await play_through(client, auth_headers, started.json())

    assert finished["is_session_finished"] is True
    assert finished["session"]["rounds_done"] == daily_service.ROUNDS_TOTAL

    templates = (
        (await db.execute(select(SeriesRound).order_by(SeriesRound.position))).scalars().all()
    )
    session_id = finished["session"]["id"]

    state = (await client.get(f"/api/sessions/{session_id}", headers=auth_headers)).json()
    played_zones = [result["zone"]["id"] for result in state["results"]]

    assert played_zones == [template.zone_id for template in templates]


async def test_finished_challenge_appears_in_the_day_table(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    registered_user,
):
    started = await client.post("/api/challenge/today/start", headers=auth_headers)
    await play_through(client, auth_headers, started.json())

    body = (await client.get("/api/challenge/today", headers=auth_headers)).json()

    assert body["finished_players"] == 1
    assert body["my_session"]["status"] == "finished"
    assert [entry["rank"] for entry in body["results"]] == [1]
    assert body["results"][0]["display_name"] == registered_user.display_name


async def test_day_table_is_sorted_by_score(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    for headers in (auth_headers, other_user_headers):
        started = await client.post("/api/challenge/today/start", headers=headers)
        await play_through(client, headers, started.json())

    results = (await client.get("/api/challenge/today", headers=auth_headers)).json()["results"]
    scores = [entry["total_score"] for entry in results]

    assert scores == sorted(scores, reverse=True)
    assert [entry["rank"] for entry in results] == [1, 2]


async def test_starting_challenge_closes_the_ordinary_game(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Незавершённая партия у игрока по-прежнему может быть только одна."""
    ordinary = await client.post(
        "/api/sessions",
        json={"rounds_total": 5},
        headers=auth_headers,
    )
    ordinary_id = ordinary.json()["session"]["id"]

    await client.post("/api/challenge/today/start", headers=auth_headers)

    state = (await client.get(f"/api/sessions/{ordinary_id}", headers=auth_headers)).json()
    assert state["session"]["status"] == "abandoned"


async def test_yesterday_challenge_does_not_block_today(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    """Сыграв вчера, сегодня играть можно."""
    started = await client.post("/api/challenge/today/start", headers=auth_headers)
    await play_through(client, auth_headers, started.json())

    session = await db.get(GameSession, started.json()["session"]["id"])
    assert session is not None
    session.challenge_day = (datetime.now(UTC) - timedelta(days=1)).date()
    await db.flush()

    again = await client.post("/api/challenge/today/start", headers=auth_headers)
    assert again.status_code == 201


async def test_challenge_round_hides_the_target(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    started = await client.post("/api/challenge/today/start", headers=auth_headers)

    assert "target" not in started.text
    assert zone.name not in started.text
