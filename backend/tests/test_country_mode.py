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
    """Где именно внутри страны игрок ткнул, роли не играет: он назвал её."""
    state = await start_country_game(client, auth_headers, zone)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"country": "RUS"},
        headers=auth_headers,
    )

    result = answer.json()["result"]
    assert result["score"] == MAX_ROUND_SCORE
    assert result["country"] == "Россия"
    assert result["guess_country"] == "Россия"
    assert float(result["distance_km"]) == 0


async def test_missing_the_country_costs_points(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    state = await start_country_game(client, auth_headers, zone)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"country": "PRT"},
        headers=auth_headers,
    )

    result = answer.json()["result"]
    assert result["score"] < MAX_ROUND_SCORE
    assert result["country"] == "Россия"
    assert result["guess_country"] == "Португалия"
    # Промах считается от места на снимке до названной страны
    assert float(result["distance_km"]) > 1000


async def test_point_is_not_an_answer_about_countries(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    """
    В раунде про страны отвечают страной.

    Раньше игрок ставил точку, а сервер сам смотрел, куда она попала. Точка в
    океане при этом не значила ничего, и раунд заканчивался нулём непонятно
    за что. Теперь выбирают страну, и промахнуться мимо суши нельзя.
    """
    state = await start_country_game(client, auth_headers, zone)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": -30.0, "latitude": 0.0},
        headers=auth_headers,
    )

    assert answer.status_code == 400, answer.text


async def test_unknown_country_is_refused(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    state = await start_country_game(client, auth_headers, zone)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"country": "ZZZ"},
        headers=auth_headers,
    )

    assert answer.status_code == 400, answer.text


async def test_country_is_not_an_answer_in_a_usual_round(
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
        json={"country": "RUS"},
        headers=auth_headers,
    )

    assert answer.status_code == 400, answer.text


async def test_answer_needs_exactly_one_form(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    borders: None,
):
    """И точка, и страна разом — ошибка клиента, а не повод угадывать."""
    state = await start_country_game(client, auth_headers, zone)

    both = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"longitude": 37.6, "latitude": 55.7, "country": "RUS"},
        headers=auth_headers,
    )
    assert both.status_code == 422

    neither = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={},
        headers=auth_headers,
    )
    assert neither.status_code == 422


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


# ─── Контуры для карты догадки ───────────────────────────────────────────


async def test_borders_come_as_geojson_with_codes(
    client: AsyncClient,
    auth_headers: dict,
    borders: None,
):
    """По этим контурам игрок и тыкает: без кода страны ответ не отправить."""
    response = await client.get("/api/countries/borders", headers=auth_headers)

    assert response.status_code == 200
    collection = response.json()

    assert collection["type"] == "FeatureCollection"
    codes = {feature["properties"]["code"] for feature in collection["features"]}
    assert codes == {"RUS", "PRT"}

    names = {feature["properties"]["name"] for feature in collection["features"]}
    assert names == {"Россия", "Португалия"}

    for feature in collection["features"]:
        assert feature["geometry"]["type"] in {"Polygon", "MultiPolygon"}


async def test_borders_are_open_to_guests(client: AsyncClient, borders: None):
    """
    Токен для контуров не нужен: те же границы нужны гостю в знакомстве с
    игрой, а к разгадке они никого не приближают — на карте лежат границы всех
    стран сразу, и какая из них правильная, по ним не узнать.
    """
    assert (await client.get("/api/countries/borders")).status_code == 200


async def test_borders_are_cacheable(client: AsyncClient, auth_headers: dict, borders: None):
    """Полмегабайта на каждый раунд качать незачем."""
    response = await client.get("/api/countries/borders", headers=auth_headers)

    assert "max-age" in response.headers["Cache-Control"]
    assert response.headers["ETag"]


# ─── Условия партии ──────────────────────────────────────────────────────


async def test_country_group_is_refused_in_country_mode(
    client: AsyncClient,
    auth_headers: dict,
):
    """«Россия» в условиях партии — это готовый ответ на все её раунды."""
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "answer_mode": "country", "country_group": "russia"},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_country_group_is_fine_in_a_usual_game(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "country_group": "russia"},
        headers=auth_headers,
    )

    assert response.status_code == 201
