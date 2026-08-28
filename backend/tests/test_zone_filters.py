"""Тесты фильтров игровых зон: часть света и группа стран."""

import pytest
from geoalchemy2 import WKTElement
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.enums import COUNTRY_GROUPS, CountryGroup, group_countries
from app.models.location_zone import LocationZone
from app.services import zones as zones_service
from tests.conftest import TEST_POLYGON
from tests.helpers import play_through


async def make_zone(
    db: AsyncSession,
    name: str,
    country: str,
    continent: str,
    category: str = "city",
    tier: str = "normal",
) -> LocationZone:
    """Активная зона в заданной стране."""
    zone = LocationZone(
        name=name,
        description="Квадрат для теста фильтров",
        category=category,
        tier=tier,
        country=country,
        continent=continent,
        polygon=WKTElement(TEST_POLYGON, srid=4326),
        is_active=True,
    )
    db.add(zone)
    await db.flush()
    return zone


@pytest.fixture
async def zones_in_countries(db: AsyncSession) -> None:
    """По зоне на каждую из групп и одна вне их всех."""
    await make_zone(db, "Москва", "Россия", "europe")
    await make_zone(db, "Нью-Йорк", "США", "north_america")
    await make_zone(db, "Рим", "Италия", "europe")
    await make_zone(db, "Токио", "Япония", "asia")


async def test_group_covers_only_its_countries(
    db: AsyncSession,
    zones_in_countries: None,
):
    found = await zones_service.list_zones(db, country_group=CountryGroup.EU)

    assert [zone.name for zone in found] == ["Рим"]


async def test_random_zone_stays_inside_the_group(
    db: AsyncSession,
    zones_in_countries: None,
):
    for _ in range(10):
        zone = await zones_service.pick_random_zone(db, country_group=CountryGroup.RUSSIA)
        assert zone.country == "Россия"


async def test_empty_intersection_is_reported(
    db: AsyncSession,
    zones_in_countries: None,
):
    # Россия и Азия по отдельности зоны находят, вместе — ни одной
    with pytest.raises(NotFoundError):
        await zones_service.pick_random_zone(
            db,
            continent="asia",
            country_group=CountryGroup.RUSSIA,
        )


async def test_endpoint_filters_by_group(
    client: AsyncClient,
    auth_headers: dict,
    zones_in_countries: None,
):
    response = await client.get("/api/zones?country_group=usa", headers=auth_headers)

    assert response.status_code == 200
    assert [zone["country"] for zone in response.json()] == ["США"]


@pytest.fixture
async def zones_of_every_level(db: AsyncSession) -> None:
    """По зоне на каждый уровень."""
    await make_zone(db, "Париж", "Франция", "europe", category="city", tier="easy")
    await make_zone(db, "Гамбург", "Германия", "europe", category="city", tier="normal")
    await make_zone(db, "Тоскана", "Италия", "europe", category="rural", tier="hard")
    await make_zone(db, "Гоби", "Монголия", "asia", category="desert", tier="hardcore")


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        ("easy", "Париж"),
        ("normal", "Гамбург"),
        ("hard", "Тоскана"),
        ("hardcore", "Гоби"),
    ],
)
async def test_level_picks_its_own_places(
    db: AsyncSession,
    zones_of_every_level: None,
    level: str,
    expected: str,
):
    """Хардкор не должен подсовывать город, а лёгкий — пустыню."""
    found = await zones_service.list_zones(db, difficulty=level)

    assert [zone.name for zone in found] == [expected]


async def test_levels_do_not_share_zones(db: AsyncSession, zones_of_every_level: None):
    """
    Зона живёт ровно на одном уровне.

    Раньше «легко» было подмножеством «средне»: Париж — город, а значит,
    попадался и там. Уровень, который включает в себя соседний, ничего не
    обещает игроку: выбрав «средне», он всё равно мог получить Манхэттен.
    """
    seen: set[str] = set()

    for level in ("easy", "normal", "hard", "hardcore"):
        names = {zone.name for zone in await zones_service.list_zones(db, difficulty=level)}
        assert not (seen & names), f"{level}: зона уже занята другим уровнем"
        seen |= names


async def test_level_beats_the_category(db: AsyncSession):
    """
    Из категории уровень не выводится, и город городу рознь.

    Гуанчжоу больше Амстердама, но с воздуха узнают второй — поэтому оба
    «city», а уровни у них разные.
    """
    await make_zone(db, "Амстердам", "Нидерланды", "europe", category="city", tier="easy")
    await make_zone(db, "Гуанчжоу", "Китай", "asia", category="city", tier="hard")

    easy = {zone.name for zone in await zones_service.list_zones(db, difficulty="easy")}
    hard = {zone.name for zone in await zones_service.list_zones(db, difficulty="hard")}

    assert easy == {"Амстердам"}
    assert hard == {"Гуанчжоу"}


async def test_unknown_level_is_rejected(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/zones?difficulty=невозможно", headers=auth_headers)

    assert response.status_code == 422


async def test_unknown_group_is_rejected(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/zones?country_group=mars", headers=auth_headers)

    assert response.status_code == 422


async def test_every_group_has_countries():
    for group in CountryGroup:
        assert group_countries(group), f"группа {group} пуста"


async def test_country_names_are_unique_across_groups():
    seen: set[str] = set()

    for countries in COUNTRY_GROUPS.values():
        overlap = seen & set(countries)
        assert not overlap, f"страна в двух группах сразу: {overlap}"
        seen |= set(countries)


async def test_game_stays_inside_the_group(
    client: AsyncClient,
    auth_headers: dict,
    zones_in_countries: None,
):
    """Партия с фильтром по группе не выходит за её страны."""
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 3, "view_extent_km": 15.0, "country_group": "usa"},
        headers=auth_headers,
    )
    assert started.status_code == 201, started.text

    # Страна раунда — часть ответа, а не активного раунда: до ответа игрок её
    # знать не должен, поэтому проверяем по завершённой партии
    state = started.json()
    await play_through(client, auth_headers, state)

    played = await client.get(f"/api/sessions/{state['session']['id']}", headers=auth_headers)
    assert played.status_code == 200

    countries = [item["zone"]["country"] for item in played.json()["results"]]
    assert countries == ["США"] * 3


async def test_continent_holds_for_every_round(
    client: AsyncClient,
    auth_headers: dict,
    zones_in_countries: None,
):
    """Условия набора действуют на всю партию, а не только на первый раунд."""
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 3, "view_extent_km": 15.0, "continent": "europe"},
        headers=auth_headers,
    )
    assert started.status_code == 201, started.text

    state = started.json()
    await play_through(client, auth_headers, state)

    played = await client.get(f"/api/sessions/{state['session']['id']}", headers=auth_headers)
    continents = {item["zone"]["continent"] for item in played.json()["results"]}

    assert continents == {"europe"}
