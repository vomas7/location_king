"""
Знакомство с игрой без учётной записи.

Главное, что здесь проверяется, — не игра, а её отсутствие в базе: гость
проходит пять раундов, и после него не остаётся ни партии, ни раунда, ни
строки в таблице лидеров. Ровно на этом когда-то разошлись с гостями, и
вернуть их можно было только так.

Границы в тестах свои — прямоугольники вместо настоящего OSM: проверяются
правила, а не точность карты.
"""

import re
from pathlib import Path

import pytest
from geoalchemy2 import WKTElement
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country
from app.models.enums import AnswerMode
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.services import demo as demo_service
from app.services.scoring import MAX_ROUND_SCORE

#: Коробки вокруг мест знакомства и несколько далёких стран, чтобы режиму
#: выбора было из чего собрать шесть вариантов
BORDERS: dict[str, tuple[str, str]] = {
    "RUS": ("Россия", "MULTIPOLYGON(((30 50, 30 65, 50 65, 50 50, 30 50)))"),
    "FRA": ("Франция", "MULTIPOLYGON(((0 45, 0 51, 6 51, 6 45, 0 45)))"),
    "USA": ("США", "MULTIPOLYGON(((-80 35, -80 45, -70 45, -70 35, -80 35)))"),
    "EGY": ("Египет", "MULTIPOLYGON(((25 22, 25 32, 35 32, 35 22, 25 22)))"),
    "GBR": ("Великобритания", "MULTIPOLYGON(((-6 50, -6 56, 2 56, 2 50, -6 50)))"),
    "BRA": ("Бразилия", "MULTIPOLYGON(((-60 -20, -60 -5, -45 -5, -45 -20, -60 -20)))"),
    "AUS": ("Австралия", "MULTIPOLYGON(((115 -35, 115 -20, 140 -20, 140 -35, 115 -35)))"),
    "IND": ("Индия", "MULTIPOLYGON(((70 10, 70 28, 88 28, 88 10, 70 10)))"),
    "ZAF": ("ЮАР", "MULTIPOLYGON(((18 -34, 18 -25, 32 -25, 32 -34, 18 -34)))"),
    "ARG": ("Аргентина", "MULTIPOLYGON(((-70 -50, -70 -30, -58 -30, -58 -50, -70 -50)))"),
    "CHN": ("Китай", "MULTIPOLYGON(((100 25, 100 45, 125 45, 125 25, 100 25)))"),
}

#: Центры мест знакомства. Полигон вокруг каждого делается квадратом в
#: полградуса: точное место здесь не важно, важно, в какую страну оно попало
CENTERS: dict[str, tuple[float, float]] = {
    "Москва, центр": (37.62, 55.75),
    "Париж": (2.35, 48.86),
    "Нью-Йорк, Манхэттен": (-73.97, 40.78),
    "Пирамиды Гизы": (31.13, 29.98),
    "Лондон": (-0.13, 51.51),
}


def _square(lon: float, lat: float, half: float = 0.05) -> str:
    west, east = lon - half, lon + half
    south, north = lat - half, lat + half
    return (
        f"POLYGON(({west} {south}, {west} {north}, {east} {north}, {east} {south}, {west} {south}))"
    )


@pytest.fixture
async def demo_catalog(db: AsyncSession) -> None:
    """Границы стран и пять зон знакомства — всё, на чём оно собирается."""
    db.add_all(
        [
            Country(code=code, name=name, border=WKTElement(border, srid=4326))
            for code, (name, border) in BORDERS.items()
        ]
    )

    db.add_all(
        [
            LocationZone(
                name=name,
                description="Место знакомства",
                category="city",
                tier="easy",
                country=BORDERS[code][0],
                polygon=WKTElement(_square(lon, lat), srid=4326),
                is_active=True,
            )
            for name, (lon, lat), code in zip(
                CENTERS.keys(),
                CENTERS.values(),
                ("RUS", "FRA", "USA", "EGY", "GBR"),
                strict=True,
            )
        ]
    )
    await db.flush()


async def _rounds(client: AsyncClient) -> list[dict]:
    response = await client.get("/api/demo/rounds")
    assert response.status_code == 200, response.text
    return response.json()["rounds"]


# ─── Состав экскурсии ────────────────────────────────────────────────────


async def test_five_rounds_without_any_token(client: AsyncClient, demo_catalog: None):
    """Знакомство открывается без авторизации — в этом весь его смысл."""
    rounds = await _rounds(client)

    assert len(rounds) == demo_service.DEMO_ROUNDS
    assert [item["index"] for item in rounds] == [1, 2, 3, 4, 5]


async def test_modes_go_from_simple_to_real(client: AsyncClient, demo_catalog: None):
    """Три раунда на выбор, потом карта стран, в конце точка."""
    rounds = await _rounds(client)

    assert [item["answer_mode"] for item in rounds] == [
        AnswerMode.CHOICE,
        AnswerMode.CHOICE,
        AnswerMode.CHOICE,
        AnswerMode.COUNTRY,
        AnswerMode.POINT,
    ]


async def test_choice_rounds_offer_six_countries(client: AsyncClient, demo_catalog: None):
    rounds = await _rounds(client)

    for item in rounds[:3]:
        assert len(item["choices"]) == 6

    # В остальных режимах список не нужен: там отвечают по карте
    assert rounds[3]["choices"] == []
    assert rounds[4]["choices"] == []


async def test_round_hides_the_answer(client: AsyncClient, demo_catalog: None):
    """
    В раунде нет ни координат цели, ни того, какой вариант верный.

    То же правило, что и в настоящей игре: до ответа клиент не получает
    ничего, по чему можно вычислить цель.
    """
    rounds = await _rounds(client)

    for item in rounds:
        assert "target" not in item
        assert "country_code" not in item
        assert "/api/demo/rounds/" in item["tiles_url"]

    for choice in rounds[0]["choices"]:
        assert set(choice) == {"code", "name"}


async def test_no_hints_are_sold(client: AsyncClient, demo_catalog: None):
    """Знакомство и так вся подсказка: продавать в нём нечего."""
    for item in await _rounds(client):
        assert item["hint"] is None
        assert item["hint_cost"] == 0
        assert item["deadline_at"] is None


# ─── Ответы ──────────────────────────────────────────────────────────────


async def test_right_country_takes_everything(
    client: AsyncClient, db: AsyncSession, demo_catalog: None
):
    prepared = await demo_service.rounds(db)
    correct = prepared[0].country_code

    response = await client.post("/api/demo/rounds/1/guess", json={"country": correct})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["score"] == MAX_ROUND_SCORE
    assert body["country"] == body["guess_country"]
    assert body["zone"]["name"] == "Москва, центр"


async def test_wrong_country_is_worth_less(
    client: AsyncClient, db: AsyncSession, demo_catalog: None
):
    prepared = await demo_service.rounds(db)
    wrong = next(code for code in prepared[0].choices if code != prepared[0].country_code)

    response = await client.post("/api/demo/rounds/1/guess", json={"country": wrong})

    assert response.status_code == 200, response.text
    assert response.json()["score"] < MAX_ROUND_SCORE


async def test_country_outside_the_offered_six_is_refused(
    client: AsyncClient, db: AsyncSession, demo_catalog: None
):
    """Иначе список вариантов был бы украшением: запрос собирается и руками."""
    prepared = await demo_service.rounds(db)
    outside = next(code for code in BORDERS if code not in prepared[0].choices)

    response = await client.post("/api/demo/rounds/1/guess", json={"country": outside})

    assert response.status_code == 400, response.text


async def test_point_round_scores_by_distance(
    client: AsyncClient, db: AsyncSession, demo_catalog: None
):
    prepared = await demo_service.rounds(db)
    target = prepared[4]

    near = await client.post(
        "/api/demo/rounds/5/guess",
        json={"longitude": target.target_lon, "latitude": target.target_lat},
    )
    far = await client.post(
        "/api/demo/rounds/5/guess",
        json={"longitude": target.target_lon + 40, "latitude": target.target_lat - 30},
    )

    assert near.status_code == 200, near.text
    assert far.status_code == 200, far.text
    assert near.json()["score"] > far.json()["score"]
    assert float(near.json()["distance_km"]) < float(far.json()["distance_km"])


async def test_result_looks_like_a_real_one(
    client: AsyncClient, db: AsyncSession, demo_catalog: None
):
    """
    Итог отдаётся той же схемой, что и у настоящего раунда.

    На этом держится переиспользование экрана результата: он не должен знать,
    гость перед ним или игрок.
    """
    prepared = await demo_service.rounds(db)

    response = await client.post(
        "/api/demo/rounds/1/guess", json={"country": prepared[0].country_code}
    )

    assert response.status_code == 200, response.text
    assert set(response.json()) == {
        "id",
        "index",
        "status",
        "view_extent_km",
        "target",
        "guess",
        "distance_km",
        "score",
        "max_score",
        "accuracy",
        "country",
        "guess_country",
        "answer_seconds",
        "zone",
        "guessed_at",
    }


async def test_point_round_reveals_the_target_after_the_answer(
    client: AsyncClient, db: AsyncSession, demo_catalog: None
):
    """Раунд закончен — цель уже можно показать, иначе линию промаха не нарисовать."""
    prepared = await demo_service.rounds(db)

    response = await client.post(
        "/api/demo/rounds/5/guess", json={"longitude": 10.0, "latitude": 40.0}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["target"] == [
        pytest.approx(prepared[4].target_lon),
        pytest.approx(prepared[4].target_lat),
    ]
    assert body["guess"] == [10.0, 40.0]


async def test_country_answer_in_a_point_round_is_refused(client: AsyncClient, demo_catalog: None):
    response = await client.post("/api/demo/rounds/5/guess", json={"country": "RUS"})
    assert response.status_code == 400, response.text


async def test_point_answer_in_a_choice_round_is_refused(client: AsyncClient, demo_catalog: None):
    response = await client.post(
        "/api/demo/rounds/1/guess", json={"longitude": 37.6, "latitude": 55.7}
    )
    assert response.status_code == 400, response.text


async def test_unknown_round_is_not_found(client: AsyncClient, demo_catalog: None):
    response = await client.post("/api/demo/rounds/99/guess", json={"country": "RUS"})
    assert response.status_code == 404, response.text


# ─── Ничего не остаётся в базе ───────────────────────────────────────────


async def test_whole_demo_writes_nothing(client: AsyncClient, db: AsyncSession, demo_catalog: None):
    """
    Гость проходит все пять раундов, и в базе не появляется ни одной строки.

    Это главное свойство знакомства: гостевые партии пришлось бы исключать из
    таблицы лидеров, счётчика игроков и истории, а потом ещё и чистить.
    """

    async def counts() -> tuple[int, int]:
        sessions = await db.scalar(select(func.count()).select_from(GameSession))
        rounds = await db.scalar(select(func.count()).select_from(Round))
        return sessions or 0, rounds or 0

    before = await counts()

    prepared = await demo_service.rounds(db)
    for demo_round in prepared:
        payload = (
            {"country": demo_round.country_code}
            if demo_round.answer_mode.by_country
            else {"longitude": 0.0, "latitude": 0.0}
        )
        response = await client.post(f"/api/demo/rounds/{demo_round.index}/guess", json=payload)
        assert response.status_code == 200, response.text

    assert await counts() == before


async def test_demo_does_not_touch_zone_statistics(
    client: AsyncClient, db: AsyncSession, demo_catalog: None
):
    """Статистика зоны — про настоящих игроков: знакомство её не портит."""
    prepared = await demo_service.rounds(db)
    zone = await db.get(LocationZone, prepared[0].zone_id)
    assert zone is not None

    await client.post("/api/demo/rounds/1/guess", json={"country": prepared[0].country_code})
    await db.refresh(zone)

    assert zone.total_rounds == 0


async def _event(client: AsyncClient, name: str) -> int:
    """Значение счётчика события из отдаваемого Prometheus текста."""
    needle = f'location_king_events_total{{event="{name}"}}'

    for line in (await client.get("/api/metrics")).text.splitlines():
        if line.startswith(needle):
            return int(float(line.rsplit(" ", 1)[1]))
    return 0


async def test_funnel_is_counted(client: AsyncClient, db: AsyncSession, demo_catalog: None):
    """
    Начали и дошли до конца — два числа, из которых видно, работает ли
    знакомство вообще. Без них непонятно, уходят ли люди на первом снимке или
    на карте стран.
    """
    started = await _event(client, "demo_started")
    completed = await _event(client, "demo_completed")

    await client.get("/api/demo/rounds")

    prepared = await demo_service.rounds(db)
    last = prepared[-1]
    await client.post(
        f"/api/demo/rounds/{last.index}/guess",
        json={"longitude": last.target_lon, "latitude": last.target_lat},
    )

    assert await _event(client, "demo_started") == started + 1
    assert await _event(client, "demo_completed") == completed + 1


async def test_rejected_answer_is_not_a_completed_demo(client: AsyncClient, demo_catalog: None):
    """Отвергнутый запрос — это не пройденное знакомство."""
    completed = await _event(client, "demo_completed")

    # Последний раунд про точку, а прислали страну
    response = await client.post(
        f"/api/demo/rounds/{demo_service.DEMO_ROUNDS}/guess", json={"country": "RUS"}
    )

    assert response.status_code == 400, response.text
    assert await _event(client, "demo_completed") == completed


# ─── Границы стран открыты гостю ─────────────────────────────────────────


async def test_borders_open_without_a_token(client: AsyncClient, demo_catalog: None):
    """Без них четвёртый раунд знакомства не на чем играть."""
    response = await client.get("/api/countries/borders")

    assert response.status_code == 200, response.text
    assert response.json()["type"] == "FeatureCollection"


# ─── Места знакомства против настоящего каталога ─────────────────────────

SEED = Path(__file__).resolve().parents[1] / "scripts" / "seed.py"


def test_demo_places_exist_in_the_catalog():
    """
    Знакомство названо местами по именам, и каталог правят руками.

    Переименовали зону — и гость с посадочной страницы получает 404 вместо
    игры, причём молча: он просто не приходит. Заметить это некому, поэтому
    замечает тест — он читает seed.py, как и проверка переводов рядом.
    """
    catalog = set(re.findall(r'\n        name="([^"]+)"', SEED.read_text(encoding="utf-8")))

    missing = [
        place.zone_name for place in demo_service.DEMO_PLACES if place.zone_name not in catalog
    ]

    assert missing == [], f"нет в каталоге: {missing}"


def test_demo_shows_every_way_to_answer():
    """
    Знакомство — экскурсия по трём режимам, а не пять одинаковых раундов.

    Если один из режимов выпадет, приглашение в конце начнёт обещать то, чего
    человек не пробовал, и это будет заметно только по цифрам воронки.
    """
    modes = {place.answer_mode for place in demo_service.DEMO_PLACES}

    assert modes == {AnswerMode.CHOICE, AnswerMode.COUNTRY, AnswerMode.POINT}
    # Порядок от простого к настоящему: список, карта стран, точка
    assert demo_service.DEMO_PLACES[0].answer_mode is AnswerMode.CHOICE
    assert demo_service.DEMO_PLACES[-1].answer_mode is AnswerMode.POINT
