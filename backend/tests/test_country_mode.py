"""
Режим «угадай страну».

Границы в тестах свои — два прямоугольника вместо настоящего OSM: проверяется
не точность карты, а правила игры. Настоящие границы проверяются отдельно, на
каталоге зон.
"""

import pytest
from geoalchemy2 import WKTElement
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.country import Country
from app.models.enums import AnswerMode
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.services import series as series_service
from app.services.scoring import MAX_ROUND_SCORE, country_score

#: Коробка вокруг тестовой зоны под Москвой и вторая — далеко на западе
RUSSIA = "MULTIPOLYGON(((30 50, 30 65, 50 65, 50 50, 30 50)))"
PORTUGAL = "MULTIPOLYGON(((-10 37, -10 42, -6 42, -6 37, -10 37)))"


@pytest.fixture
async def borders(db: AsyncSession) -> None:
    """Две страны: одна вокруг тестовой зоны, вторая на другом конце Европы."""
    db.add_all(
        [
            Country(code="RUS", name="Россия", border=WKTElement(RUSSIA, srid=4326)),
            Country(code="PRT", name="Португалия", border=WKTElement(PORTUGAL, srid=4326)),
        ]
    )
    await db.flush()


async def start_country_game(client: AsyncClient, headers: dict, zone: LocationZone) -> dict:
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id, "answer_mode": "country"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# ─── Очки ────────────────────────────────────────────────────────────────


def test_right_country_takes_everything():
    assert country_score(True, 0.0) == MAX_ROUND_SCORE


def test_wrong_country_never_reaches_the_top():
    """Соседняя страна — осмысленный ответ, но не тот же самый."""
    assert country_score(False, 0.0) < MAX_ROUND_SCORE / 2 + 1


def test_far_miss_costs_everything():
    assert country_score(False, 20_000) == 0


def test_closer_miss_is_worth_more():
    assert country_score(False, 100) > country_score(False, 900)


# ─── Раунд ───────────────────────────────────────────────────────────────


async def test_round_says_what_it_asks(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    """Клиент не должен догадываться, о чём его спрашивают."""
    state = await start_country_game(client, auth_headers, zone)

    assert state["current_round"]["answer_mode"] == AnswerMode.COUNTRY

    usual = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id},
        headers=auth_headers,
    )
    assert usual.json()["current_round"]["answer_mode"] == AnswerMode.POINT


async def test_target_country_is_fixed_when_the_series_is_built(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
    db: AsyncSession,
):
    """
    У всех, кто играет одну серию, правильный ответ обязан быть один.

    Поэтому страна цели считается один раз — при сборке серии, а не на каждую
    догадку.
    """
    state = await start_country_game(client, auth_headers, zone)

    stored = (
        await db.execute(select(Round).where(Round.id == state["current_round"]["id"]))
    ).scalar_one()

    assert stored.country_code == "RUS"


async def test_hitting_the_country_scores_full(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    """Промах в километрах здесь не важен: вопрос был про страну."""
    state = await start_country_game(client, auth_headers, zone)

    # Точка далеко от цели, но внутри той же страны
    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": 45.0, "latitude": 60.0},
        headers=auth_headers,
    )

    result = answer.json()["result"]
    assert result["score"] == MAX_ROUND_SCORE
    assert result["country"] == "Россия"
    assert result["guess_country"] == "Россия"
    assert float(result["distance_km"]) > 500


async def test_missing_the_country_costs_points(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    state = await start_country_game(client, auth_headers, zone)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": -8.0, "latitude": 39.0},
        headers=auth_headers,
    )

    result = answer.json()["result"]
    assert result["score"] < MAX_ROUND_SCORE
    assert result["country"] == "Россия"
    assert result["guess_country"] == "Португалия"


async def test_answer_in_the_ocean_names_no_country(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    """Океан — это не страна, и притворяться, что игрок куда-то попал, нечестно."""
    state = await start_country_game(client, auth_headers, zone)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": -30.0, "latitude": 0.0},
        headers=auth_headers,
    )

    result = answer.json()["result"]
    assert result["guess_country"] is None
    assert result["score"] == 0


async def test_usual_round_says_nothing_about_countries(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id},
        headers=auth_headers,
    )
    answer = await client.post(
        f"/api/rounds/{started.json()['current_round']['id']}/guess",
        json={"longitude": 37.6, "latitude": 55.7},
        headers=auth_headers,
    )

    result = answer.json()["result"]
    assert result["country"] is None
    assert result["guess_country"] is None


async def test_zone_the_borders_disagree_with_is_refused(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
    borders: None,
):
    """
    Каталог говорит одно, границы другое — такое место в режим стран не идёт.

    Иначе правильным ответом окажется не та страна, которую игрок увидит в
    результате: ровно это происходит с Монако, которого в границах нет вовсе.
    """
    from tests.conftest import TEST_POLYGON

    zone = LocationZone(
        name="Спорное место",
        description="Каталог обещает Финляндию, границы дают Россию",
        category="city",
        tier="normal",
        country="Финляндия",
        continent="europe",
        polygon=WKTElement(TEST_POLYGON, srid=4326),
        is_active=True,
    )
    db.add(zone)
    await db.flush()

    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id, "answer_mode": "country"},
        headers=auth_headers,
    )

    assert response.status_code == 404


async def test_series_without_borders_cannot_be_built(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
):
    """Границы не загружены — режим стран честно не работает, а не врёт."""
    with pytest.raises(NotFoundError):
        await series_service.create(
            db,
            rounds_total=1,
            view_extent_km=15.0,
            zone_id=zone.id,
            answer_mode=AnswerMode.COUNTRY,
        )
