"""
Партии, начатые до перехода на серии раундов.

Условия набора у них нигде не сохранены, продолжить их нечем. Проверяем, что
игрок при этом не оказывается запертым: догадка принимается, счёт остаётся,
партия закрывается.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SessionStatus
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone


async def test_guess_closes_a_session_without_series(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    zone: LocationZone,
):
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 3, "view_extent_km": 15.0},
        headers=auth_headers,
    )
    assert started.status_code == 201, started.text
    state = started.json()

    # Ровно то состояние, в котором остались партии от прошлой версии
    session = (
        await db.execute(select(GameSession).where(GameSession.id == state["session"]["id"]))
    ).scalar_one()
    session.series_id = None
    await db.flush()

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": 37.6, "latitude": 55.7},
        headers=auth_headers,
    )

    assert answer.status_code == 200, answer.text
    body = answer.json()

    # Догадка засчитана, а не потеряна вместе с ошибкой
    assert body["result"]["score"] >= 0
    assert body["next_round"] is None
    assert body["is_session_finished"] is True

    await db.refresh(session)
    # Брошенная, а не завершённая: до конца партия не дошла, и в статистике
    # она не должна выглядеть сыгранной полностью
    assert session.status == SessionStatus.ABANDONED
    assert session.is_active is False
