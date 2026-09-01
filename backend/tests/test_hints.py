"""
Подсказка в раунде.

Проверяется и то, что она раскрывает, и то, чего не раскрывает: координат в
ней нет, а бесполезную подсказку сервер не продаёт.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_zone import LocationZone
from app.models.round import Round
from app.models.series import RoundSeries
from app.services import game as game_service
from app.services.hints import choose
from app.services.scoring import MAX_ROUND_SCORE, score_after_hint

# Максимум раунда после подсказки — считаем один раз и сверяем с ним ответы
AFTER_HINT = score_after_hint(MAX_ROUND_SCORE)


def make_zone(**overrides) -> LocationZone:
    """Зона в памяти: choose работает с данными, а не с базой."""
    values = {
        "name": "Зона",
        "category": "city",
        "continent": "europe",
        "country": "Франция",
        "region": "Прованс",
    }
    values.update(overrides)
    return LocationZone(**values)


def series(**overrides) -> RoundSeries:
    values = {"difficulty": None, "continent": None, "country_group": None}
    values.update(overrides)
    return RoundSeries(**values)


# ─── Что раскрывать ──────────────────────────────────────────────────────


def test_world_game_gets_the_continent():
    hint = choose(make_zone(), series(), "ru")

    assert hint is not None
    assert hint.label == "Часть света"
    assert hint.value == "Европа"


def test_chosen_continent_moves_the_hint_to_the_country():
    hint = choose(make_zone(), series(continent="europe"), "ru")

    assert hint is not None
    assert hint.label == "Страна"
    assert hint.value == "Франция"


def test_single_country_game_moves_the_hint_to_the_region():
    hint = choose(
        make_zone(country="Россия", region="Камчатка"), series(country_group="russia"), "ru"
    )

    assert hint is not None
    assert hint.label == "Регион"
    assert hint.value == "Камчатка"


def test_group_of_many_countries_still_reveals_the_country():
    """Евросоюз — это двадцать семь стран, и знать, какая из них, полезно."""
    hint = choose(make_zone(), series(country_group="eu"), "ru")

    assert hint is not None
    assert hint.label == "Страна"


def test_hint_falls_through_empty_fields():
    """У зоны без части света подсказка съезжает на страну."""
    hint = choose(make_zone(continent=None), series(), "ru")

    assert hint is not None
    assert hint.label == "Страна"


def test_nothing_left_to_reveal():
    """Партия по одной стране и зона без региона: добавить нечего."""
    zone = make_zone(country="Россия", region=None, continent=None)

    assert choose(zone, series(country_group="russia"), "ru") is None


def test_series_without_conditions_behaves_like_the_whole_world():
    """Партия, собранная до того, как условия начали запоминать."""
    hint = choose(make_zone(), None, "ru")

    assert hint is not None
    assert hint.label == "Часть света"


# ─── Как она берётся ─────────────────────────────────────────────────────


async def start_round(client: AsyncClient, headers: dict, zone: LocationZone) -> dict:
    response = await client.post(
        "/api/sessions",
        json={"rounds_total": 2, "view_extent_km": 5.0, "zone_id": zone.id},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["current_round"]


async def test_hint_costs_part_of_the_round(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    opened = await start_round(client, auth_headers, zone)
    assert opened["max_score"] == MAX_ROUND_SCORE
    assert opened["hint"] is None
    assert opened["hint_cost"] == MAX_ROUND_SCORE - AFTER_HINT

    response = await client.post(f"/api/rounds/{opened['id']}/hint", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["hint"] == {"label": "Страна", "value": "Россия"}
    assert body["max_score"] == AFTER_HINT
    assert AFTER_HINT < MAX_ROUND_SCORE

    # Взятая подсказка больше не продаётся, и цену за неё не показывают
    assert body["hint_cost"] == 0


async def test_hint_carries_no_coordinates(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
):
    opened = await start_round(client, auth_headers, zone)
    body = (await client.post(f"/api/rounds/{opened['id']}/hint", headers=auth_headers)).text

    stored = (await db.execute(select(Round).where(Round.id == opened["id"]))).scalar_one()

    for field in ("target", "latitude", "longitude", "tile_x", "tile_y", "tile_zoom"):
        assert field not in body

    assert str(stored.tile_x) not in body.replace(str(stored.id), "")


async def test_hint_is_taken_once(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    opened = await start_round(client, auth_headers, zone)

    assert (
        await client.post(f"/api/rounds/{opened['id']}/hint", headers=auth_headers)
    ).status_code == 200
    again = await client.post(f"/api/rounds/{opened['id']}/hint", headers=auth_headers)

    assert again.status_code == 409


async def test_hint_survives_a_reload(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Текст подсказки нигде не хранится — он должен собираться заново."""
    opened = await start_round(client, auth_headers, zone)
    await client.post(f"/api/rounds/{opened['id']}/hint", headers=auth_headers)

    reloaded = (await client.get(f"/api/rounds/{opened['id']}", headers=auth_headers)).json()

    assert reloaded["hint"] == {"label": "Страна", "value": "Россия"}
    assert reloaded["max_score"] == AFTER_HINT


async def test_guess_after_hint_is_scored_against_the_lower_maximum(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
):
    opened = await start_round(client, auth_headers, zone)
    await client.post(f"/api/rounds/{opened['id']}/hint", headers=auth_headers)

    stored = (await db.execute(select(Round).where(Round.id == opened["id"]))).scalar_one()
    target_lon, target_lat = await _target(db, stored)

    result = (
        await client.post(
            f"/api/rounds/{opened['id']}/guess",
            json={"longitude": target_lon, "latitude": target_lat},
            headers=auth_headers,
        )
    ).json()["result"]

    assert result["max_score"] == AFTER_HINT
    assert result["score"] <= AFTER_HINT


async def test_hint_is_not_sold_for_a_closed_round(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    opened = await start_round(client, auth_headers, zone)
    await client.post(
        f"/api/rounds/{opened['id']}/guess",
        json={"longitude": 37.6, "latitude": 55.7},
        headers=auth_headers,
    )

    late = await client.post(f"/api/rounds/{opened['id']}/hint", headers=auth_headers)

    assert late.status_code == 409


async def test_hint_of_a_stranger_is_forbidden(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    opened = await start_round(client, auth_headers, zone)

    response = await client.post(f"/api/rounds/{opened['id']}/hint", headers=other_user_headers)

    assert response.status_code == 403


async def _target(db: AsyncSession, round_obj: Round) -> tuple[float, float]:
    return await game_service.target_coordinates(db, round_obj)
