"""
Режим выбора: шесть названий вместо карты.

Вход в игру для тех, кто по карте пока не ориентируется. Проверяется, что
список честный: правильный ответ в нём есть, но по нему не догадаться, а
ответить чем-то, чего не предлагали, нельзя.

Границы здесь свои — несколько прямоугольников вместо настоящего OSM.
"""

import pytest
from geoalchemy2 import WKTElement
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.models.enums import AnswerMode
from app.models.location_zone import LocationZone
from app.services import countries as countries_service

#: Страна вокруг тестовой зоны под Москвой
RUSSIA = "MULTIPOLYGON(((30 50, 30 65, 50 65, 50 50, 30 50)))"

#: Далёкие страны: каждая дальше тысячи километров от Москвы, поэтому все
#: годятся в неверные варианты
FAR = {
    "PRT": "MULTIPOLYGON(((-10 37, -10 42, -6 42, -6 37, -10 37)))",
    "BRA": "MULTIPOLYGON(((-60 -20, -60 -10, -50 -10, -50 -20, -60 -20)))",
    "JPN": "MULTIPOLYGON(((135 34, 135 40, 141 40, 141 34, 135 34)))",
    "ZAF": "MULTIPOLYGON(((20 -34, 20 -26, 30 -26, 30 -34, 20 -34)))",
    "CAN": "MULTIPOLYGON(((-120 50, -120 60, -100 60, -100 50, -120 50)))",
    "AUS": "MULTIPOLYGON(((120 -30, 120 -20, 140 -20, 140 -30, 120 -30)))",
}

#: Сосед вплотную к зоне: в варианты попадать не должен
NEIGHBOUR = "MULTIPOLYGON(((50 50, 50 65, 52 65, 52 50, 50 50)))"


@pytest.fixture
async def world(db: AsyncSession) -> None:
    db.add(Country(code="RUS", name="Россия", border=WKTElement(RUSSIA, srid=4326)))
    db.add(Country(code="BLR", name="Сосед", border=WKTElement(NEIGHBOUR, srid=4326)))
    for code, border in FAR.items():
        db.add(Country(code=code, name=f"Страна {code}", border=WKTElement(border, srid=4326)))
    await db.flush()


async def start(client: AsyncClient, headers: dict, zone: LocationZone) -> dict:
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id, "answer_mode": "choice"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_round_offers_six_options(
    client: AsyncClient, auth_headers: dict, zone: LocationZone, world: None
):
    state = await start(client, auth_headers, zone)
    round_view = state["current_round"]

    assert round_view["answer_mode"] == AnswerMode.CHOICE
    assert len(round_view["choices"]) == countries_service.CHOICES
    assert {"RUS"} <= {choice["code"] for choice in round_view["choices"]}

    # У каждого варианта есть название: игрок выбирает из слов, а не из кодов
    assert all(choice["name"] for choice in round_view["choices"])


async def test_options_do_not_give_the_answer_away(
    client: AsyncClient, auth_headers: dict, zone: LocationZone, world: None
):
    """
    Правильный вариант не стоит на одном и том же месте.

    Иначе его выбирали бы не глядя на снимок. Двадцать раундов подряд: если
    порядок не перемешан, правильный будет на одной позиции во всех.
    """
    positions = set()

    for _ in range(20):
        state = await start(client, auth_headers, zone)
        codes = [choice["code"] for choice in state["current_round"]["choices"]]
        positions.add(codes.index("RUS"))

    assert len(positions) > 1


async def test_wrong_options_are_far_away(
    client: AsyncClient, auth_headers: dict, zone: LocationZone, world: None
):
    """Сосед вплотную к зоне в варианты не идёт: снимок его не отличает."""
    for _ in range(10):
        state = await start(client, auth_headers, zone)
        codes = {choice["code"] for choice in state["current_round"]["choices"]}

        assert "BLR" not in codes


async def test_answering_with_an_option_scores(
    client: AsyncClient, auth_headers: dict, zone: LocationZone, world: None
):
    state = await start(client, auth_headers, zone)

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"country": "RUS"},
        headers=auth_headers,
    )

    result = answer.json()["result"]
    assert result["score"] > 0
    assert result["guess_country"] == "Россия"


async def test_a_country_that_was_not_offered_is_refused(
    client: AsyncClient, auth_headers: dict, zone: LocationZone, world: None
):
    """
    Иначе список вариантов — украшение.

    Запрос можно собрать и руками, и без этой проверки правильную страну
    подбирали бы перебором всех, минуя шесть предложенных.
    """
    state = await start(client, auth_headers, zone)
    offered = {choice["code"] for choice in state["current_round"]["choices"]}
    missing = ({"BLR", *FAR} - offered).pop()

    answer = await client.post(
        f"/api/rounds/{state['current_round']['id']}/guess",
        json={"country": missing},
        headers=auth_headers,
    )

    assert answer.status_code == 400, answer.text


async def test_ordinary_country_round_has_no_options(
    client: AsyncClient, auth_headers: dict, zone: LocationZone, world: None
):
    """Там карта со странами — список названий был бы вторым ответом."""
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "zone_id": zone.id, "answer_mode": "country"},
        headers=auth_headers,
    )

    round_view = response.json()["current_round"]
    assert round_view["answer_mode"] == AnswerMode.COUNTRY
    assert round_view["choices"] == []


async def test_options_survive_a_reload(
    client: AsyncClient, auth_headers: dict, zone: LocationZone, world: None
):
    """
    Список не должен меняться между запросами.

    Он собирается один раз при сборке серии: иначе в комнате у соперника были
    бы свои варианты, а после перезагрузки страницы — третьи.
    """
    state = await start(client, auth_headers, zone)
    first = [choice["code"] for choice in state["current_round"]["choices"]]

    again = await client.get("/api/sessions/current", headers=auth_headers)
    second = [choice["code"] for choice in again.json()["current_round"]["choices"]]

    assert first == second


async def test_choice_mode_refuses_a_chosen_country(client: AsyncClient, auth_headers: dict):
    """«Россия» в условиях партии — готовый ответ на все её раунды."""
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 1, "answer_mode": "choice", "country_group": "russia"},
        headers=auth_headers,
    )

    assert response.status_code == 422
