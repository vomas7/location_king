"""
Достопримечательности — отдельный слой каталога.

Не города, а объекты, которые узнают сами по себе: Колизей, Тадж-Махал,
Пальма Джумейра. Показываются крупным планом, и в этом вся суть: Колизей в
кадре на сорок пять километров — это Рим, а не Колизей.

Отсюда два правила, которые здесь и проверяются: у такой зоны свой кадр, и в
обычную партию она не попадает — кадр в четыре километра посреди партии с
кадром в сорок пять это другая игра, а не разнообразие.
"""

import pytest
from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import Difficulty, ZoneCategory
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.services import series as series_service
from app.services import zones as zones_service

#: Кадр обычной партии — такой же, как у «средне»
WIDE_KM = 45.0

#: Кадр достопримечательности: объект, а не город вокруг него
CLOSE_KM = 4.0


def square(west: float, half: float = 0.05) -> str:
    return (
        f"POLYGON(({west} 55, {west} {55 + 2 * half}, "
        f"{west + 2 * half} {55 + 2 * half}, {west + 2 * half} 55, {west} 55))"
    )


@pytest.fixture
async def catalog(db: AsyncSession) -> None:
    """Город и достопримечательность рядом — как Вашингтон и Пентагон."""
    db.add(
        LocationZone(
            name="Город",
            category=ZoneCategory.CITY,
            tier=Difficulty.EASY,
            country="Страна",
            polygon=WKTElement(square(30.0), srid=4326),
            is_active=True,
        )
    )
    db.add(
        LocationZone(
            name="Объект",
            category=ZoneCategory.LANDMARK,
            tier=Difficulty.EASY,
            country="Страна",
            view_extent_km=CLOSE_KM,
            polygon=WKTElement(square(31.0), srid=4326),
            is_active=True,
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_landmarks_stay_out_of_an_ordinary_game(db: AsyncSession, catalog: None) -> None:
    """Не просил — не получил: отбор без категории их не видит."""
    for _ in range(20):
        zone = await zones_service.pick_random_zone(db)
        assert zone.category != ZoneCategory.LANDMARK


@pytest.mark.asyncio
async def test_asking_for_landmarks_gives_only_them(db: AsyncSession, catalog: None) -> None:
    for _ in range(20):
        zone = await zones_service.pick_random_zone(db, category=ZoneCategory.LANDMARK)
        assert zone.category == ZoneCategory.LANDMARK


@pytest.mark.asyncio
async def test_landmark_round_is_shot_close_up(db: AsyncSession, catalog: None) -> None:
    """
    Кадр зоны сильнее кадра партии.

    Партия заказывает сорок пять километров, а раунд по достопримечательности
    всё равно выходит крупным планом — иначе в кадре оказался бы город вокруг.
    """
    series = await series_service.create(
        db,
        rounds_total=1,
        view_extent_km=WIDE_KM,
        category=ZoneCategory.LANDMARK,
    )

    frame = float(series.rounds[0].view_extent_km)
    assert frame < WIDE_KM / 2


@pytest.mark.asyncio
async def test_ordinary_round_keeps_the_frame_of_its_game(db: AsyncSession, catalog: None) -> None:
    series = await series_service.create(db, rounds_total=1, view_extent_km=WIDE_KM)

    frame = float(series.rounds[0].view_extent_km)
    assert frame > WIDE_KM / 2


@pytest.mark.asyncio
async def test_a_landmark_game_plays_from_end_to_end(
    client, db: AsyncSession, catalog: None, auth_headers: dict[str, str]
) -> None:
    """Партия по достопримечательностям начинается и выдаёт крупный кадр."""
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "category": ZoneCategory.LANDMARK.value},
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Зона подгружается сразу: связь за пределами запроса лениво не читается
    round_obj = (await db.execute(select(Round).options(selectinload(Round.zone)))).scalars().one()

    assert round_obj.zone.category == ZoneCategory.LANDMARK
    assert float(round_obj.view_extent_km) < WIDE_KM / 2
