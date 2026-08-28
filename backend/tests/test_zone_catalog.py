"""
Проверки списка игровых зон.

Список правится руками, и ошибка в нём проявляется не при загрузке, а в
партии игрока: раунд посреди океана или дубль зоны в выдаче.
"""

import re
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    COUNTRY_GROUPS,
    Continent,
    Difficulty,
    ZoneCategory,
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


#: Категории, где точка раунда обязана остаться в застройке: иначе игрок
#: получает поле вместо города.
URBAN_CATEGORIES = {"city", "coast", "historical", "architecture", "industrial"}

#: Точка раунда берётся из квадрата вокруг центра и в углу отходит от него в
#: полтора раза дальше — до семи километров. Вид по умолчанию пятнадцать
#: километров, то есть семь с половиной в каждую сторону: центр места остаётся
#: в кадре. При десяти километрах радиуса он уходил за край, и «Париж»
#: показывал безымянный пригород.
MAX_URBAN_RADIUS_KM = 5

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


def test_every_zone_has_a_known_tier():
    for zone in ZONES:
        assert zone.tier in set(Difficulty), f"{zone.name}: неизвестный уровень {zone.tier}"


def test_every_difficulty_has_zones():
    """Пустой уровень — это тупик: игрок выбирает и получает отказ."""
    tiers = {zone.tier for zone in ZONES}

    for level in Difficulty:
        assert level in tiers, f"на уровне {level} нет ни одной зоны"


def test_no_level_swallows_the_catalog():
    """
    Уровень, в который попала половина каталога, уровнем не является.

    Ровно это и случилось, когда уровень выводился из категории: «средне»
    оказалось четырьмя пятыми списка и складывало Гамбург с Сурабаей.
    """
    for level in Difficulty:
        share = sum(zone.tier == level for zone in ZONES) / len(ZONES)
        assert share <= 0.5, f"на уровне {level} — {share:.0%} каталога"


def test_wild_places_are_hardcore_only():
    """
    Дикая природа не должна попадаться тому, кто её не выбирал.

    Это и было главной жалобой: на среднем уровне игроку доставалась саванна.
    """
    wild = {"nature", "mountains", "desert", "polar"}

    for zone in ZONES:
        if zone.category in wild:
            assert zone.tier == Difficulty.HARDCORE, zone.name


def test_easy_and_normal_are_built_up_places():
    """На двух нижних уровнях игрок ищет город, а не местность."""
    for zone in ZONES:
        if zone.tier in {Difficulty.EASY, Difficulty.NORMAL}:
            assert zone.category in URBAN_CATEGORIES, f"{zone.name} ({zone.category})"


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


def test_readme_counts_match_the_catalog():
    """
    Таблица уровней в README должна сходиться с каталогом.

    Числа в ней проверяемые, а значит, однажды разойдутся с правдой: зоны
    добавляют, а таблицу поправить забывают.
    """
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")

    rows = re.findall(r"^\| (Легко|Средне|Сложно|Хардкор)\s*\|[^|]+\|\s*(\d+) \|$", readme, re.M)
    assert len(rows) == len(Difficulty), "в README не все уровни"

    levels = {
        "Легко": Difficulty.EASY,
        "Средне": Difficulty.NORMAL,
        "Сложно": Difficulty.HARD,
        "Хардкор": Difficulty.HARDCORE,
    }

    for title, claimed in rows:
        actual = sum(zone.tier == levels[title] for zone in ZONES)
        assert actual == int(claimed), f"{title}: в README {claimed}, в каталоге {actual}"
