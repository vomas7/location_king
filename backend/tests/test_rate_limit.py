"""Тесты ограничения частоты запросов."""

import pytest
from httpx import AsyncClient

from app.models.location_zone import LocationZone
from app.services import rate_limit
from app.services.rate_limit import Limit, RateLimit


async def test_repeated_login_attempts_are_throttled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Перебор пароля упирается в лимит, а не в бесконечные попытки."""
    monkeypatch.setitem(rate_limit.RULES, Limit.LOGIN, RateLimit(limit=3, window_seconds=60))

    payload = {"email": "nobody@example.com", "password": "wrong password"}
    statuses = [(await client.post("/api/auth/login", json=payload)).status_code for _ in range(5)]

    assert statuses[:3] == [401, 401, 401]
    assert statuses[3:] == [429, 429]


async def test_throttled_response_says_when_to_retry(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setitem(rate_limit.RULES, Limit.REGISTER, RateLimit(limit=1, window_seconds=120))

    body = {"email": "first@example.com", "password": "long enough password"}
    assert (await client.post("/api/auth/register", json=body)).status_code == 201

    second = await client.post(
        "/api/auth/register",
        json={"email": "second@example.com", "password": "long enough password"},
    )

    assert second.status_code == 429
    assert "Retry-After" in second.headers
    assert 0 < int(second.headers["Retry-After"]) <= 120
    assert "Слишком часто" in second.json()["detail"]


async def test_starting_sessions_is_throttled(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setitem(
        rate_limit.RULES, Limit.START_SESSION, RateLimit(limit=2, window_seconds=60)
    )

    body = {"rounds_total": 1}
    statuses = [
        (await client.post("/api/sessions", json=body, headers=auth_headers)).status_code
        for _ in range(3)
    ]

    assert statuses == [201, 201, 429]


async def test_limits_are_counted_per_player(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
    monkeypatch: pytest.MonkeyPatch,
):
    """Один игрок, упёршийся в лимит, не мешает другому."""
    monkeypatch.setitem(
        rate_limit.RULES, Limit.START_SESSION, RateLimit(limit=1, window_seconds=60)
    )

    body = {"rounds_total": 1}
    assert (await client.post("/api/sessions", json=body, headers=auth_headers)).status_code == 201
    assert (await client.post("/api/sessions", json=body, headers=auth_headers)).status_code == 429

    other = await client.post("/api/sessions", json=body, headers=other_user_headers)
    assert other.status_code == 201


async def test_limiter_lets_requests_through_when_redis_is_down(
    monkeypatch: pytest.MonkeyPatch,
):
    """Недоступный Redis не должен закрывать игру."""
    from redis.exceptions import ConnectionError as RedisConnectionError

    class BrokenRedis:
        async def incr(self, _key: str) -> int:
            raise RedisConnectionError("нет соединения")

    monkeypatch.setattr(rate_limit, "redis_client", lambda: BrokenRedis())
    monkeypatch.setitem(rate_limit.RULES, Limit.LOGIN, RateLimit(limit=1, window_seconds=60))

    # Ошибки нет: запрос просто не учитывается
    await rate_limit.check(Limit.LOGIN, "someone")
    await rate_limit.check(Limit.LOGIN, "someone")
