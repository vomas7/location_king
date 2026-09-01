"""
Ширину кадра задаёт уровень, а не игрок.

Раньше рядом с уровнем стоял отдельный переключатель «размер участка», и это
был самый непонятный элемент меню: два независимых регулятора сложности легко
сводились в бессмысленную пару — дикая природа в кадре на пять километров не
угадывается никак.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Difficulty
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.schemas.game import StartSessionRequest
from app.services import difficulty as difficulty_service


def test_every_level_has_its_own_frame():
    frames = [difficulty_service.view_extent_km(level) for level in Difficulty]

    assert len(set(frames)) == len(frames)
    assert all(frame > 0 for frame in frames)


def test_unknown_level_falls_back_to_the_default():
    assert difficulty_service.view_extent_km(None) == difficulty_service.DEFAULT_VIEW_EXTENT_KM
    assert (
        difficulty_service.view_extent_km("нет такого уровня")
        == difficulty_service.DEFAULT_VIEW_EXTENT_KM
    )


def test_request_without_frame_takes_it_from_the_level():
    request = StartSessionRequest(difficulty=Difficulty.HARDCORE)

    assert request.view_extent_km is None
    assert request.frame_km == difficulty_service.view_extent_km(Difficulty.HARDCORE)


def test_explicit_frame_still_wins():
    """Комната и челлендж задают кадр сами: правило про уровень им не мешает."""
    request = StartSessionRequest(difficulty=Difficulty.EASY, view_extent_km=12.5)

    assert request.frame_km == 12.5


@pytest.mark.asyncio
async def test_started_round_uses_the_frame_of_its_level(
    client: AsyncClient,
    db: AsyncSession,
    zone: LocationZone,
    auth_headers: dict[str, str],
) -> None:
    zone.tier = Difficulty.HARD
    await db.flush()

    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "difficulty": Difficulty.HARD},
        headers=auth_headers,
    )
    assert response.status_code == 201

    round_obj = (await db.execute(select(Round))).scalars().one()
    assert float(round_obj.view_extent_km) == pytest.approx(
        difficulty_service.view_extent_km(Difficulty.HARD), abs=1.0
    )
