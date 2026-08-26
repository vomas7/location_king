"""
Тесты главного свойства игры: до догадки клиент не может узнать, где цель.

Проверяется и то, чего нет в ответах, и то, что прокси тайлов не выпускает за
пределы показанной области.
"""

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.models.round import Round
from app.services import tiles as tiles_service
from app.services.game import max_local_zoom

# Минимальный валидный JPEG-заголовок — содержимое тайла для теста
FAKE_TILE = b"\xff\xd8\xff\xe0" + b"tile-bytes" * 8


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Подменить тайловый сервер и записывать запрошенные адреса."""
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, content=FAKE_TILE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(tiles_service, "_get_http_client", lambda: client)

    return requested


@pytest.fixture
def no_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Отключить кэш, чтобы считать обращения к провайдеру."""

    async def miss(_key: str) -> None:
        return None

    async def noop(_key: str, _tile: bytes) -> None:
        return None

    monkeypatch.setattr(tiles_service, "_cache_get", miss)
    monkeypatch.setattr(tiles_service, "_cache_set", noop)


async def start(client: AsyncClient, headers: dict) -> dict:
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 2, "view_extent_km": 5.0},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def stored_round(db: AsyncSession, round_id: int) -> Round:
    return (await db.execute(select(Round).where(Round.id == round_id))).scalar_one()


async def test_start_response_carries_no_coordinates(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
):
    state = await start(client, auth_headers)
    round_obj = await stored_round(db, state["current_round"]["id"])

    body = (
        await client.post(
            "/api/sessions",
            json={"rounds_total": 1, "zone_id": zone.id},
            headers=auth_headers,
        )
    ).text

    for field in ("target", "latitude", "longitude", "tile_x", "tile_y", "tile_zoom"):
        assert field not in body

    # Номера тайла тоже не должны попадать в ответ ни в каком виде
    assert str(round_obj.tile_x) not in body.replace(str(round_obj.id), "")


async def test_active_round_response_carries_no_coordinates(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]

    body = (await client.get(f"/api/rounds/{round_id}", headers=auth_headers)).json()

    assert set(body) == {
        "id",
        "index",
        "status",
        "view_extent_km",
        "max_zoom",
        "tiles_url",
        "attribution",
        "created_at",
    }


async def test_active_round_does_not_reveal_the_zone(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Название зоны — это почти ответ, до догадки его показывать нельзя."""
    state = await start(client, auth_headers)

    assert (
        zone.name
        not in (
            await client.get(f"/api/sessions/{state['session']['id']}", headers=auth_headers)
        ).text
    )


async def test_target_appears_only_after_the_guess(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]

    before = (
        await client.get(f"/api/sessions/{state['session']['id']}", headers=auth_headers)
    ).text
    assert "target" not in before

    after = await client.post(
        f"/api/rounds/{round_id}/guess",
        json={"longitude": 37.6, "latitude": 55.7},
        headers=auth_headers,
    )
    result = after.json()["result"]

    stored = await stored_round(db, round_id)
    target_lon, target_lat = result["target"]

    assert result["zone"]["name"] == zone.name
    assert stored.tile_zoom > 0
    assert -180 <= target_lon <= 180
    assert -90 <= target_lat <= 90


async def test_tile_proxy_returns_provider_bytes(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    provider: list[str],
    no_cache: None,
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]

    response = await client.get(f"/api/rounds/{round_id}/tiles/0/0/0.jpg", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == FAKE_TILE
    assert len(provider) == 1


async def test_tile_proxy_translates_local_coordinates(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
    provider: list[str],
    no_cache: None,
):
    """Локальный тайл (2, 1, 3) — это потомок тайла раунда, а не он сам."""
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]
    stored = await stored_round(db, round_id)

    await client.get(f"/api/rounds/{round_id}/tiles/2/1/3.jpg", headers=auth_headers)

    expected_z = stored.tile_zoom + 2
    expected_x = stored.tile_x * 4 + 1
    expected_y = stored.tile_y * 4 + 3

    assert provider[-1].endswith(f"/{expected_z}/{expected_y}/{expected_x}")


async def test_root_tile_is_the_round_tile(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
    provider: list[str],
    no_cache: None,
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]
    stored = await stored_round(db, round_id)

    await client.get(f"/api/rounds/{round_id}/tiles/0/0/0.jpg", headers=auth_headers)

    assert provider[-1].endswith(f"/{stored.tile_zoom}/{stored.tile_y}/{stored.tile_x}")


@pytest.mark.parametrize(("z", "x", "y"), [(0, 1, 0), (0, 0, 1), (1, 2, 0), (2, 0, 4), (3, 8, 8)])
async def test_tile_outside_the_area_is_not_found(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    provider: list[str],
    z: int,
    x: int,
    y: int,
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]

    response = await client.get(
        f"/api/rounds/{round_id}/tiles/{z}/{x}/{y}.jpg", headers=auth_headers
    )

    assert response.status_code == 404
    assert provider == []


async def test_zoom_beyond_limit_is_not_found(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
    provider: list[str],
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]
    stored = await stored_round(db, round_id)
    beyond = max_local_zoom(stored) + 1

    response = await client.get(
        f"/api/rounds/{round_id}/tiles/{beyond}/0/0.jpg",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert provider == []


async def test_declared_max_zoom_is_actually_available(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    provider: list[str],
    no_cache: None,
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]
    max_zoom = state["current_round"]["max_zoom"]
    side = 2**max_zoom

    response = await client.get(
        f"/api/rounds/{round_id}/tiles/{max_zoom}/{side - 1}/{side - 1}.jpg",
        headers=auth_headers,
    )

    assert response.status_code == 200


async def test_tiles_require_authorization(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    provider: list[str],
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]

    assert (await client.get(f"/api/rounds/{round_id}/tiles/0/0/0.jpg")).status_code == 401
    assert provider == []


async def test_tiles_of_a_foreign_round_are_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
    provider: list[str],
):
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]

    response = await client.get(
        f"/api/rounds/{round_id}/tiles/0/0/0.jpg",
        headers=other_user_headers,
    )

    assert response.status_code == 403
    assert provider == []


async def test_provider_failure_becomes_bad_gateway(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    monkeypatch: pytest.MonkeyPatch,
    no_cache: None,
):
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    monkeypatch.setattr(
        tiles_service,
        "_get_http_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(failing)),
    )

    state = await start(client, auth_headers)
    response = await client.get(
        f"/api/rounds/{state['current_round']['id']}/tiles/0/0/0.jpg",
        headers=auth_headers,
    )

    assert response.status_code == 502


async def test_second_request_is_served_from_cache(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    provider: list[str],
):
    """Кэш есть — значит, провайдера дёргаем один раз на тайл."""
    state = await start(client, auth_headers)
    round_id = state["current_round"]["id"]

    first = await client.get(f"/api/rounds/{round_id}/tiles/1/0/1.jpg", headers=auth_headers)
    second = await client.get(f"/api/rounds/{round_id}/tiles/1/0/1.jpg", headers=auth_headers)

    assert first.content == second.content == FAKE_TILE
    assert len(provider) == 1
