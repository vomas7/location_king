"""
Счётчики игроков.

Единственный публичный запрос без авторизации: числа видны на первом экране
ещё до того, как игрок вошёл. Поэтому проверяется и то, что он отвечает без
токена, и то, что ничего, кроме чисел, наружу не уходит.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import redis_client
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.user import User
from app.services import community as community_service
from app.services.auth import register
from tests.helpers import play_through


@pytest.mark.asyncio
async def test_counts_registered_players(
    client: AsyncClient, db: AsyncSession, registered_user: User
) -> None:
    response = await client.get("/api/community")

    assert response.status_code == 200
    assert response.json() == {"players": 1, "playing": 0}


@pytest.mark.asyncio
async def test_answers_without_a_token(client: AsyncClient) -> None:
    """Первый экран показывает число до входа: авторизации у запроса нет."""
    response = await client.get("/api/community")

    assert response.status_code == 200
    assert response.json()["players"] >= 0


@pytest.mark.asyncio
async def test_nothing_but_the_number_leaks(
    client: AsyncClient, db: AsyncSession, registered_user: User
) -> None:
    """Ни имён, ни почты, ни разбивки: это счётчик, а не выгрузка."""
    body = (await client.get("/api/community")).json()

    assert set(body) == {"players", "playing"}


@pytest.mark.asyncio
async def test_second_request_is_served_from_cache(
    client: AsyncClient, db: AsyncSession, registered_user: User
) -> None:
    """
    Запрос публичный и по игроку не ограничивается: от нагрузки его защищает
    кэш, а не лимит. Значит, второй ответ обязан прийти из него.
    """
    assert (await client.get("/api/community")).json()["players"] == 1

    await register(db, "one-more@example.com", "another long password", "Ещё один")
    await db.flush()

    assert (await client.get("/api/community")).json()["players"] == 1


@pytest.mark.asyncio
async def test_counts_those_playing_right_now(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
) -> None:
    """Число обещает живых людей за экранами — значит, начатые партии."""
    assert (await client.get("/api/community")).json()["playing"] == 0

    await redis_client().delete(community_service.PLAYING_KEY)
    started = await client.post("/api/sessions", json={}, headers=auth_headers)
    assert started.status_code == 201

    assert (await client.get("/api/community")).json()["playing"] == 1


@pytest.mark.asyncio
async def test_finished_game_is_not_playing_now(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
) -> None:
    started = await client.post("/api/sessions", json={}, headers=auth_headers)
    await play_through(client, auth_headers, started.json())

    await redis_client().delete(community_service.PLAYING_KEY)

    assert (await client.get("/api/community")).json()["playing"] == 0


@pytest.mark.asyncio
async def test_old_game_is_not_playing_now(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
) -> None:
    """Партия, начатая позавчера и брошенная, — это не «сейчас играет»."""
    started = await client.post("/api/sessions", json={}, headers=auth_headers)
    session = (
        await db.execute(
            select(GameSession).where(GameSession.id == started.json()["session"]["id"])
        )
    ).scalar_one()
    session.started_at = datetime.now(UTC) - community_service.PLAYING_WINDOW - timedelta(minutes=1)
    await db.flush()

    await redis_client().delete(community_service.PLAYING_KEY)

    assert (await client.get("/api/community")).json()["playing"] == 0
