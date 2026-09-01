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
from app.services import series as series_service


def test_frame_never_shrinks_as_content_gets_harder():
    """
    Кадр растёт вслед за размером зоны: чем больше зона, тем больше нужно
    контекста, чтобы место вообще можно было прочитать. Совпадать у соседних
    уровней он при этом может — у «легко» и «средне» зоны одного размера.
    """
    frames = [
        difficulty_service.view_extent_km(level)
        for level in (Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD, Difficulty.HARDCORE)
    ]

    assert frames == sorted(frames)
    assert all(frame > 0 for frame in frames)


def test_no_level_shows_an_unreadable_square():
    """
    Кадр до двадцати километров показывает сетку кварталов, по которой нельзя
    опознать даже Шанхай: на первых полутысячах раундов такие кадры давали
    средний промах в 4170 километров против 2895 у кадров пошире.
    """
    for level in Difficulty:
        assert difficulty_service.view_extent_km(level) >= 40.0


def test_unknown_level_falls_back_to_the_default():
    assert difficulty_service.view_extent_km(None) == difficulty_service.DEFAULT_VIEW_EXTENT_KM
    assert (
        difficulty_service.view_extent_km("нет такого уровня")
        == difficulty_service.DEFAULT_VIEW_EXTENT_KM
    )


def test_request_without_frame_leaves_it_to_the_level():
    """Запрос кадра не выдумывает: пустое поле доезжает до серии как пустое."""
    assert StartSessionRequest(difficulty=Difficulty.HARDCORE).view_extent_km is None


@pytest.mark.asyncio
async def test_series_without_frame_takes_it_from_the_level(
    db: AsyncSession, zone: LocationZone
) -> None:
    zone.tier = Difficulty.HARDCORE
    await db.flush()

    series = await series_service.create(db, rounds_total=1, difficulty=Difficulty.HARDCORE)
    wanted = difficulty_service.view_extent_km(Difficulty.HARDCORE)

    assert 0.5 < float(series.rounds[0].view_extent_km) / wanted < 2.0


@pytest.mark.asyncio
async def test_explicit_frame_still_wins(db: AsyncSession, zone: LocationZone) -> None:
    """Комната и челлендж задают кадр сами: правило про уровень им не мешает."""
    zone.tier = Difficulty.HARDCORE
    await db.flush()

    series = await series_service.create(
        db, rounds_total=1, view_extent_km=12.5, difficulty=Difficulty.HARDCORE
    )
    hardcore = difficulty_service.view_extent_km(Difficulty.HARDCORE)

    assert float(series.rounds[0].view_extent_km) < hardcore / 2


@pytest.mark.asyncio
async def test_started_round_uses_the_frame_of_its_level(
    client: AsyncClient,
    db: AsyncSession,
    zone: LocationZone,
    auth_headers: dict[str, str],
) -> None:
    """
    Кадр раунда — ближайший к заказанному тайл, а не ровно заказанное число:
    участок это один тайл Web Mercator, его ширина зависит от широты, а соседние
    зумы отличаются вдвое. Поэтому проверяется то, что действительно
    выполняется: полученный кадр отстоит от заказанного меньше чем на зум.
    """
    zone.tier = Difficulty.HARDCORE
    await db.flush()

    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "difficulty": Difficulty.HARDCORE},
        headers=auth_headers,
    )
    assert response.status_code == 201

    round_obj = (await db.execute(select(Round))).scalars().one()
    wanted = difficulty_service.view_extent_km(Difficulty.HARDCORE)

    assert 0.5 < float(round_obj.view_extent_km) / wanted < 2.0
