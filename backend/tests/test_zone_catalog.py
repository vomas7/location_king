"""
Проверки списка игровых зон.

Список правится руками, и ошибка в нём проявляется не при загрузке, а в
партии игрока: раунд посреди океана или дубль зоны в выдаче.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    COUNTRY_GROUPS,
    DIFFICULTY_CATEGORIES,
    ZONE_COLLECTIONS,
    Continent,
    Difficulty,
    ZoneCategory,
    ZoneCollection,
)
from app.models.location_zone import LocationZone
from app.utils.geo import haversine_km
from scripts.seed import ZONES, seed


def test_names_are_unique():
    names = [zone.name for zone in ZONES]

    assert len(names) == len(set(names)), "зона встречается в списке дважды"


def test_coordinates_are_on_the_planet():
    for zone in ZONES:
        assert -180 <= zone.longitude <= 180, zone.name
        # Веб-Меркатор обрывается у полюсов, и зона за этой границей дала бы
        # раунд, который невозможно показать
        assert -85 <= zone.latitude <= 85, zone.name


#: Категории городских уровней. Точка раунда здесь обязана остаться в
#: застройке, иначе игрок получает поле вместо города.
URBAN_CATEGORIES = set(DIFFICULTY_CATEGORIES[Difficulty.NORMAL])

#: Точка раунда берётся из квадрата вокруг центра, поэтому в углу она отходит
#: от него ещё в полтора раза дальше. Десять километров — это уже до
#: пятнадцати от центра города, дальше начинаются поля.
MAX_URBAN_RADIUS_KM = 10

#: Дикая местность попадается только тем, кто выбрал её сам, и там большой
#: разброс — часть замысла: искать приходится по рельефу, а не по кварталам.
MAX_RADIUS_KM = 200


def test_zone_is_big_enough_for_a_round():
    for zone in ZONES:
        assert 3 <= zone.radius_km <= MAX_RADIUS_KM, zone.name


def test_city_rounds_stay_inside_the_city():
    """
    Радиус городской зоны ограничен.

    Иначе точка уходит за окраину, и «Лос-Анджелес» показывает горный хребет
    в тридцати километрах от города — ровно на это и жаловались игроки.
    """
    for zone in ZONES:
        if zone.category in URBAN_CATEGORIES:
            assert zone.radius_km <= MAX_URBAN_RADIUS_KM, zone.name


def test_every_difficulty_has_zones():
    """Пустой уровень — это тупик: игрок выбирает и получает отказ."""
    categories = {zone.category for zone in ZONES}
    names = {zone.name for zone in ZONES}

    for level in Difficulty:
        if level is Difficulty.EASY:
            assert names & set(ZONE_COLLECTIONS[ZoneCollection.MAJOR_CITIES])
        else:
            assert categories & set(DIFFICULTY_CATEGORIES[level]), level


def test_difficulty_levels_do_not_overlap():
    """Категория принадлежит одному уровню: иначе «хардкор» выдавал бы города."""
    seen: set[str] = set()

    for level, members in DIFFICULTY_CATEGORIES.items():
        overlap = seen & set(members)
        assert not overlap, f"{level}: категории уже заняты — {overlap}"
        seen |= set(members)


def test_categories_and_continents_are_known():
    for zone in ZONES:
        assert zone.category in set(ZoneCategory), zone.name
        assert zone.continent in set(Continent), zone.name


def test_polygon_is_closed():
    for zone in ZONES:
        wkt = zone.polygon_wkt()
        points = wkt.removeprefix("POLYGON((").removesuffix("))").split(", ")

        assert len(points) == 5, zone.name
        assert points[0] == points[-1], f"полигон {zone.name} не замкнут"


def test_zones_do_not_duplicate_each_other():
    """
    Два центра рядом означают, что место добавили дважды.

    Пять километров — с запасом: даже соседние достопримечательности вроде
    Каира и пирамид Гизы разнесены сильнее.
    """
    for i, first in enumerate(ZONES):
        for second in ZONES[i + 1 :]:
            distance = haversine_km(
                first.longitude, first.latitude, second.longitude, second.latitude
            )
            assert distance > 5, f"{first.name} и {second.name} — одно и то же место"


def test_collections_name_real_zones():
    """Подборка хранит имена: опечатка или переименование выкинули бы место молча."""
    names = {zone.name for zone in ZONES}

    for collection, members in ZONE_COLLECTIONS.items():
        missing = set(members) - names
        assert not missing, f"в подборке {collection} нет таких зон: {sorted(missing)}"


def test_major_cities_are_cities():
    """Подборка обещает города — каналы и пирамиды в неё попадать не должны."""
    by_name = {zone.name: zone for zone in ZONES}

    for name in ZONE_COLLECTIONS[ZoneCollection.MAJOR_CITIES]:
        assert by_name[name].category in {"city", "coast", "historical"}, name


def test_every_country_group_has_zones():
    """Фильтр по стране не должен приводить к пустой выдаче."""
    countries = {zone.country for zone in ZONES}

    for group, members in COUNTRY_GROUPS.items():
        assert countries & set(members), f"под группу {group} нет ни одной зоны"


@pytest.mark.parametrize("continent", list(Continent))
def test_continent_filter_has_zones_or_is_absent(continent: str):
    """
    Часть света либо представлена зонами, либо её не предлагают в меню.

    Пустой пункт фильтра — это тупик: игрок выбирает и получает отказ.
    """
    present = {zone.continent for zone in ZONES}
    offered = {"europe", "asia", "africa", "north_america", "south_america", "oceania"}

    if continent in offered:
        assert continent in present, f"{continent} предлагается в меню, но зон нет"


async def test_seed_retires_zones_that_left_the_list(db: AsyncSession):
    """Зона, убранная из списка, перестаёт попадаться, но не исчезает."""
    stale = LocationZone(
        name="Зона, которой больше нет в списке",
        description="Осталась от прошлой редакции",
        category="city",
        country="Нигде",
        continent="europe",
        polygon=ZONES[0].polygon_wkt(),
        is_active=True,
    )
    db.add(stale)
    await db.flush()

    added, updated, retired = await seed(db)

    assert retired >= 1
    assert added + updated == len(ZONES)

    found = (
        await db.execute(select(LocationZone).where(LocationZone.name == stale.name))
    ).scalar_one()
    assert found.is_active is False
