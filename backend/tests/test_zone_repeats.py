"""
Одна и та же территория не выпадает дважды за партию.

Самая частая жалоба игроков: пять раундов, и два из них про один и тот же
город. Случайный выбор без памяти так и работает — на каталоге в три сотни
зон совпадение в партии из пяти раундов встречается чаще, чем кажется.

Запрет мягкий: под узкими условиями зон в каталоге бывает меньше, чем раундов
в партии, и жёсткий запрет означал бы, что партия просто не начнётся.
"""

import pytest
from geoalchemy2 import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.services import series as series_service

#: Кадр раундов. Такой же, как в первой партии новичка
VIEW_KM = 40.0


def square(west: float) -> str:
    """Квадрат в градусе от заданной долготы: зоны в тесте не пересекаются."""
    return f"POLYGON(({west} 55, {west} 55.5, {west + 0.5} 55.5, {west + 0.5} 55, {west} 55))"


async def make_zones(db: AsyncSession, count: int, continent: str | None = None) -> None:
    """Несколько активных зон подряд, каждая на своём месте."""
    for index in range(count):
        db.add(
            LocationZone(
                name=f"Зона {index}",
                description="Квадрат",
                category="city",
                country="Россия",
                continent=continent,
                polygon=WKTElement(square(30.0 + index), srid=4326),
                is_active=True,
            )
        )
    await db.flush()


@pytest.mark.asyncio
async def test_zones_do_not_repeat_when_catalog_allows(db: AsyncSession) -> None:
    # Зон ровно столько, сколько раундов: случайный выбор без памяти дал бы
    # все шесть разными в полутора случаях из ста, так что проверка настоящая
    await make_zones(db, count=6)

    series = await series_service.create(db, rounds_total=6, view_extent_km=VIEW_KM)

    zone_ids = [item.zone_id for item in series.rounds]
    assert len(set(zone_ids)) == 6


@pytest.mark.asyncio
async def test_short_catalog_still_makes_a_full_series(db: AsyncSession) -> None:
    # Зон меньше, чем раундов: партия обязана собраться, пусть и с повтором,
    # и обе зоны обязаны быть использованы, прежде чем начнутся повторы
    await make_zones(db, count=2)

    series = await series_service.create(db, rounds_total=5, view_extent_km=VIEW_KM)

    assert len(series.rounds) == 5
    assert len({item.zone_id for item in series.rounds}) == 2


@pytest.mark.asyncio
async def test_single_zone_is_used_for_every_round(db: AsyncSession) -> None:
    # Одна зона на весь каталог: исключать нечего, и партия идёт по ней
    await make_zones(db, count=1)

    series = await series_service.create(db, rounds_total=3, view_extent_km=VIEW_KM)

    assert len({item.zone_id for item in series.rounds}) == 1


@pytest.mark.asyncio
async def test_exclusion_respects_filters(db: AsyncSession) -> None:
    # Под фильтр попадают три зоны из десяти: повтор появится на четвёртом
    # раунде, а до него все раунды обязаны быть разными
    await make_zones(db, count=3, continent="europe")
    await make_zones(db, count=7, continent="asia")

    series = await series_service.create(
        db, rounds_total=3, view_extent_km=VIEW_KM, continent="europe"
    )

    assert len({item.zone_id for item in series.rounds}) == 3
