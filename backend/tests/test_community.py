"""
Счётчик игроков.

Единственный публичный запрос без авторизации: число видно на первом экране
ещё до того, как игрок вошёл. Поэтому проверяется и то, что он отвечает без
токена, и то, что ничего, кроме числа, наружу не уходит.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import community as community_service
from app.services.auth import register


@pytest.fixture(autouse=True)
async def _clean_cache() -> None:
    """
    Кэш живёт в Redis дольше теста, а число игроков в каждом тесте своё.

    Без этого второй тест увидел бы счётчик первого: транзакция теста
    откатывается, а ключ в Redis — нет.
    """
    from app.cache import redis_client

    await redis_client().delete(community_service.CACHE_KEY)


@pytest.mark.asyncio
async def test_counts_registered_players(
    client: AsyncClient, db: AsyncSession, registered_user: User
) -> None:
    response = await client.get("/api/community")

    assert response.status_code == 200
    assert response.json() == {"players": 1}


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

    assert set(body) == {"players"}


@pytest.mark.asyncio
async def test_second_request_is_served_from_cache(
    client: AsyncClient, db: AsyncSession, registered_user: User
) -> None:
    """
    Запрос публичный и по игроку не ограничивается: от нагрузки его защищает
    кэш, а не лимит. Значит, второй ответ обязан прийти из него.
    """
    assert (await client.get("/api/community")).json() == {"players": 1}

    await register(db, "one-more@example.com", "another long password", "Ещё один")
    await db.flush()

    assert (await client.get("/api/community")).json() == {"players": 1}
