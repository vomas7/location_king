"""Общие действия тестов, не привязанные к конкретному режиму игры."""

from httpx import AsyncClient


async def play_through(
    client: AsyncClient,
    headers: dict[str, str],
    state: dict,
    longitude: float = 37.6,
    latitude: float = 55.7,
) -> dict:
    """
    Доиграть партию до конца и вернуть последний ответ.

    По умолчанию точка ставится в тестовую зону под Москвой. Там, где нужен
    проигравший, координаты задают другие: два одинаковых ответа дают ничью.
    """
    current = state["current_round"]
    body: dict = {}

    while current is not None:
        answer = await client.post(
            f"/api/rounds/{current['id']}/guess",
            json={"longitude": longitude, "latitude": latitude},
            headers=headers,
        )
        assert answer.status_code == 200, answer.text
        body = answer.json()
        current = body["next_round"]

    return body
