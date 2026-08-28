"""Тесты ограничения частоты запросов."""

import pytest
from httpx import AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.main import app
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

    class BrokenRedis:
        """Клиент, у которого не выходит ни одна команда."""

        def pipeline(self) -> "BrokenRedis":
            return self

        def incr(self, _key: str) -> "BrokenRedis":
            # В конвейере команды только копятся и возвращают его же
            return self

        def expire(self, _key: str, _ttl: int, nx: bool = False) -> "BrokenRedis":
            return self

        async def execute(self) -> list[int]:
            raise RedisConnectionError("нет соединения")

    monkeypatch.setattr(rate_limit, "redis_client", lambda: BrokenRedis())
    monkeypatch.setitem(rate_limit.RULES, Limit.LOGIN, RateLimit(limit=1, window_seconds=60))

    # Ошибки нет: запрос просто не учитывается
    await rate_limit.check(Limit.LOGIN, "someone")
    await rate_limit.check(Limit.LOGIN, "someone")


# ─── Правило, а не привычка ──────────────────────────────────────────────

#: Пишущие эндпоинты без своего лимита. Каждый здесь — осознанное решение, а
#: не забывчивость: все они ограничены не счётчиком, а самой игрой.
UNLIMITED_BY_DESIGN = {
    # Обновление токена ограничено сроком жизни самого токена, а лимит на нём
    # выкинул бы из игры того, у кого просто открыто много вкладок
    ("POST", "/api/auth/refresh"),
    # Закрыть можно только свою комнату, и только один раз
    ("POST", "/api/matches/{code}/close"),
    # Открытый раунд у игрока один, а партии уже ограничены
    ("POST", "/api/rounds/{round_id}/guess"),
    ("POST", "/api/rounds/{round_id}/timeout"),
    ("POST", "/api/sessions/{session_id}/finish"),
}

WRITING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


def _is_rate_limit(dependency) -> bool:
    """Это одна из обёрток limit_by_user или limit_by_address."""
    call = dependency.call
    return getattr(call, "__module__", "") == "app.dependencies" and (
        getattr(call, "__qualname__", "").startswith(("limit_by_user", "limit_by_address"))
    )


def test_every_writing_endpoint_is_limited():
    """
    Всё, что пишет в базу, ограничено по частоте.

    Это главное свойство игры, и держаться оно должно не на памяти того, кто
    добавляет эндпоинт. Появился новый пишущий маршрут без лимита — тест
    падает, и решение приходится принять осознанно.
    """
    unlimited: set[tuple[str, str]] = set()

    for route in app.routes:
        methods = getattr(route, "methods", set()) & WRITING_METHODS
        dependant = getattr(route, "dependant", None)

        if not methods or dependant is None:
            continue

        if not any(_is_rate_limit(item) for item in dependant.dependencies):
            unlimited |= {(method, route.path) for method in methods}

    assert unlimited <= UNLIMITED_BY_DESIGN, (
        f"без лимита: {sorted(unlimited - UNLIMITED_BY_DESIGN)}"
    )


def test_exceptions_list_has_no_leftovers():
    """Исключение, которого больше нет, — это ложь в списке причин."""
    paths = {
        (method, route.path) for route in app.routes for method in getattr(route, "methods", set())
    }

    assert UNLIMITED_BY_DESIGN <= paths, (
        f"маршрутов больше нет: {sorted(UNLIMITED_BY_DESIGN - paths)}"
    )
