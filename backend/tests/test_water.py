"""
Раунд не показывает открытую воду.

Точка раунда берётся случайно внутри зоны, а приморская зона наполовину
состоит из моря: Александрия — это десять километров города и столько же
Средиземного моря. Игрок получал кадр ровной синевы, по которому угадать
нельзя ничего, и терял раунд ни за что.

Сушей считаются границы стран — те же, по которым работает режим стран.
Здесь они свои, два прямоугольника вместо настоящего OSM: проверяется
правило, а не точность карты.
"""

import pytest
from geoalchemy2 import WKTElement
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.country import Country
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.services import series as series_service
from app.services import zones as zones_service

#: Суша: всё восточнее тридцатого и западнее пятидесятого градуса
LAND = "MULTIPOLYGON(((30 50, 30 65, 50 65, 50 50, 30 50)))"

#: Берег проходит по пятидесятому градусу: половина зоны на суше, половина в
#: море. Так устроен любой приморский город
COASTAL = "POLYGON((49.5 60, 49.5 60.4, 50.5 60.4, 50.5 60, 49.5 60))"

#: Целиком за берегом, и берега из кадра не видно — открытая вода
OFFSHORE = "POLYGON((52 60, 52 60.4, 53 60.4, 53 60, 52 60))"

#: Кадр раундов в тестах. Отсюда же считается, насколько далеко от центра
#: ещё может стоять берег: сорок процентов ширины, то есть шесть километров
VIEW_KM = 15.0


@pytest.fixture
async def land(db: AsyncSession) -> None:
    db.add(Country(code="RUS", name="Россия", border=WKTElement(LAND, srid=4326)))
    await db.flush()


async def add_zone(db: AsyncSession, name: str, polygon: str) -> LocationZone:
    zone = LocationZone(
        name=name,
        description="Проверка воды",
        category="city",
        tier="normal",
        country="Россия",
        continent="europe",
        polygon=WKTElement(polygon, srid=4326),
        is_active=True,
    )
    db.add(zone)
    await db.flush()
    return zone


async def test_point_of_a_coastal_zone_lands_on_shore(db: AsyncSession, land: None):
    """
    Половина зоны в море, но раунды достаются только суше.

    Двадцать точек подряд: при выборе наугад в море попала бы примерно
    половина, и вероятность случайно не заметить это исчезающе мала.
    """
    zone = await add_zone(db, "Приморский город", COASTAL)

    limit = 50 + VIEW_KM * zones_service.LAND_IN_FRAME / zones_service.KM_PER_DEGREE

    for _ in range(20):
        point = await zones_service.random_point_with_land(db, zone, VIEW_KM)
        assert point is not None

        longitude, _ = point
        assert longitude <= limit


async def test_a_wide_view_forgives_what_a_narrow_one_does_not(db: AsyncSession, land: None):
    """
    Чем шире кадр, тем дальше может стоять берег: в сотне километров вокруг
    точки он ещё виден, а в пяти — уже нет. Зона стоит в сорока километрах от
    берега, и годится она ровно для широкого вида.
    """
    zone = await add_zone(db, "Залив", "POLYGON((50.3 60, 50.3 60.2, 50.6 60.2, 50.6 60, 50.3 60))")

    assert await zones_service.random_point_with_land(db, zone, 5.0) is None
    assert await zones_service.random_point_with_land(db, zone, 100.0) is not None


async def test_zone_fully_at_sea_gives_nothing(db: AsyncSession, land: None):
    zone = await add_zone(db, "Открытое море", OFFSHORE)

    assert await zones_service.random_point_with_land(db, zone, VIEW_KM) is None


async def test_series_skips_a_zone_that_is_all_water(db: AsyncSession, land: None):
    """Морская зона в каталоге не должна ронять партию: берётся другая."""
    await add_zone(db, "Открытое море", OFFSHORE)
    dry = await add_zone(db, "Суша", "POLYGON((40 60, 40 60.4, 41 60.4, 41 60, 40 60))")

    series = await series_service.create(db, rounds_total=6, view_extent_km=VIEW_KM)

    assert {item.zone_id for item in series.rounds} == {dry.id}


async def test_a_zone_asked_for_by_name_says_it_is_water(db: AsyncSession, land: None):
    """Выбранную игроком зону молча не подменяем: отказ должен быть слышен."""
    sea = await add_zone(db, "Открытое море", OFFSHORE)

    with pytest.raises(NotFoundError):
        await series_service.create(db, rounds_total=1, view_extent_km=VIEW_KM, zone_id=sea.id)


async def test_rounds_of_a_started_game_are_on_land(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    land: None,
):
    """То же самое, но через игру целиком: цели раундов лежат на суше."""
    await add_zone(db, "Приморский город", COASTAL)

    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 10, "zone_id": None},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text

    stmt = select(func.ST_X(Round.target_point)).where(
        Round.session_id == response.json()["session"]["id"]
    )
    longitudes = list((await db.execute(stmt)).scalars().all())

    assert longitudes
    # Цель раунда — центр тайла, и он может отойти от точки на половину кадра
    assert all(longitude <= 50.5 for longitude in longitudes)


async def test_without_borders_the_game_still_deals_rounds(db: AsyncSession, zone: LocationZone):
    """
    Границы не загружены — отсеивать воду нечем, и партия идёт как раньше.

    Пустая таблица границ не должна означать, что игра не выдаёт ни одного
    раунда: это остановило бы её целиком.
    """
    series = await series_service.create(db, rounds_total=3, view_extent_km=VIEW_KM)

    assert len(series.rounds) == 3
