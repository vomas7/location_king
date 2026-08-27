"""Тесты идентификатора запроса и показателей."""

from httpx import AsyncClient

from app.observability import REQUEST_ID_HEADER, metrics


async def test_response_carries_a_request_id(client: AsyncClient):
    """По этому значению жалобу игрока можно найти в логах."""
    response = await client.get("/api/health")

    request_id = response.headers.get(REQUEST_ID_HEADER, "")
    assert request_id not in ("", "-")


async def test_incoming_request_id_is_kept(client: AsyncClient):
    """Если идентификатор проставил балансировщик, он не теряется."""
    response = await client.get("/api/health", headers={REQUEST_ID_HEADER: "from-proxy"})

    assert response.headers[REQUEST_ID_HEADER] == "from-proxy"


async def test_identifiers_differ_between_requests(client: AsyncClient):
    first = (await client.get("/api/health")).headers[REQUEST_ID_HEADER]
    second = (await client.get("/api/health")).headers[REQUEST_ID_HEADER]

    assert first != second


async def test_metrics_count_requests(client: AsyncClient):
    before = metrics.requests[("GET", "/api/health", 200)]
    await client.get("/api/health")

    assert metrics.requests[("GET", "/api/health", 200)] == before + 1


async def test_metrics_are_rendered_for_prometheus(client: AsyncClient):
    await client.get("/api/health")
    response = await client.get("/api/metrics")

    assert response.status_code == 200
    body = response.text
    assert "location_king_requests_total" in body
    assert "location_king_request_seconds_bucket" in body


async def test_metrics_group_by_route_not_by_path(client: AsyncClient, auth_headers: dict):
    """
    Иначе каждый тайл завёл бы собственную метрику.

    Проверяем на несуществующей партии: путь разный, маршрут один.
    """
    for session_id in (
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ):
        await client.get(f"/api/sessions/{session_id}", headers=auth_headers)

    body = (await client.get("/api/metrics")).text

    assert 'route="/api/sessions/{session_id}"' in body
    assert "11111111" not in body


async def test_forged_request_id_is_replaced(client: AsyncClient):
    """
    Значение из заголовка попадает в каждую строку лога и обратно в ответ.

    Поэтому принимается только безобидный набор символов: иначе в логи можно
    было бы дописывать собственные записи, а в ответ — что угодно.
    """
    response = await client.get(
        "/api/health",
        headers={REQUEST_ID_HEADER: 'abc INFO login as user "1"'},
    )

    assert response.headers[REQUEST_ID_HEADER].isalnum()


async def test_too_long_request_id_is_replaced(client: AsyncClient):
    response = await client.get("/api/health", headers={REQUEST_ID_HEADER: "x" * 500})

    assert len(response.headers[REQUEST_ID_HEADER]) < 100


async def test_histogram_has_upper_bucket_and_count(client: AsyncClient):
    """Без них Prometheus не считает это гистограммой."""
    await client.get("/api/health")
    body = (await client.get("/api/metrics")).text

    assert 'location_king_request_seconds_bucket{route="/api/health",le="+Inf"}' in body
    assert 'location_king_request_seconds_count{route="/api/health"}' in body
