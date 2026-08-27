"""Общие действия тестов, не привязанные к конкретному режиму игры."""

from httpx import AsyncClient


async def play_through(client: AsyncClient, headers: dict[str, str], state: dict) -> dict:
    """Доиграть партию до конца, отвечая наугад, и вернуть последний ответ."""
    current = state["current_round"]
    body: dict = {}

    while current is not None:
        answer = await client.post(
            f"/api/rounds/{current['id']}/guess",
            json={"longitude": 37.6, "latitude": 55.7},
            headers=headers,
        )
        assert answer.status_code == 200, answer.text
        body = answer.json()
        current = body["next_round"]

    return body
