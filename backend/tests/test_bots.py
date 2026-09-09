"""
Соперники-боты в дуэлях.

Проверяется главное свойство бота: он играет по-настоящему, но нигде не
выдаёт себя за человека. Числа игры — рейтинг, счётчик игроков, таблица
лидеров и статистика зон — должны остаться числами про людей.
"""

import random

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SessionStatus
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.match import Match
from app.models.round import Round
from app.models.user import User
from app.services import bots as bots_service
from app.utils.geo import haversine_km, point_at_distance
from tests.helpers import play_through

# ─── Промах ──────────────────────────────────────────────────────────────


def test_better_bot_misses_less():
    """Уровень должен быть уровнем, а не подписью: сильный ближе слабого."""
    rng = random.Random(1)
    weak = [bots_service.miss_for(300.0, 0.1, rng) for _ in range(400)]
    rng = random.Random(1)
    strong = [bots_service.miss_for(300.0, 0.9, rng) for _ in range(400)]

    assert sorted(weak)[200] > sorted(strong)[200]


def test_miss_follows_the_place():
    """Там, где промахиваются все, промахнётся и бот: место труднее."""
    rng = random.Random(7)
    easy = [bots_service.miss_for(10.0, 0.5, rng) for _ in range(400)]
    rng = random.Random(7)
    hard = [bots_service.miss_for(1000.0, 0.5, rng) for _ in range(400)]

    assert sorted(hard)[200] > sorted(easy)[200]


def test_bot_never_hits_the_pixel():
    """Попадание точь-в-точь не бывает даже у лучших — и у бота не бывает."""
    rng = random.Random(3)

    assert all(bots_service.miss_for(0.0, 1.0, rng) >= bots_service.CLOSEST_KM for _ in range(200))


def test_without_statistics_the_frame_decides(zone: LocationZone):
    """Пока раундов на зоне не было, среднего нет, а промах нужен."""
    assert zone.average_distance is None

    assert bots_service.typical_miss_km(zone, 40.0) == pytest.approx(
        40.0 * bots_service.UNKNOWN_MISS_FRACTION
    )
    assert bots_service.typical_miss_km(None, 40.0) == pytest.approx(
        40.0 * bots_service.UNKNOWN_MISS_FRACTION
    )


async def test_average_of_the_zone_beats_the_frame(db: AsyncSession, zone: LocationZone):
    zone.average_distance = 123.0
    await db.flush()

    assert bots_service.typical_miss_km(zone, 40.0) == pytest.approx(123.0)


# ─── Учётные записи ──────────────────────────────────────────────────────


async def test_bots_are_created_once(db: AsyncSession):
    first = await bots_service.ensure(db)
    second = await bots_service.ensure(db)

    assert len(first) == len(bots_service.BOTS)
    assert [bot.id for bot in second] == [bot.id for bot in first]
    assert all(bot.is_bot for bot in second)


async def test_bot_gets_the_opponent_of_his_level(db: AsyncSession):
    await bots_service.ensure(db)

    novice = await bots_service.pick(db, 900)
    master = await bots_service.pick(db, 1600)

    assert novice is not None and master is not None
    assert novice.rating < master.rating


async def test_bots_off_means_no_bots(db: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    await bots_service.ensure(db)
    monkeypatch.setattr(bots_service.settings, "duel_bots_enabled", False)

    assert await bots_service.pick(db, 1200) is None
    assert await bots_service.available(db) == 0


async def test_bot_is_not_findable_by_friend_code(
    db: AsyncSession, client: AsyncClient, auth_headers: dict
):
    bots = await bots_service.ensure(db)
    await db.flush()

    answer = await client.post(
        "/api/friends",
        json={"code": bots[0].friend_code},
        headers=auth_headers,
    )

    assert answer.status_code == 404


# ─── Дуэль ───────────────────────────────────────────────────────────────


@pytest.fixture
async def with_bots(db: AsyncSession) -> list[User]:
    bots = await bots_service.ensure(db)
    await db.flush()
    return bots


async def test_duel_with_bot_starts_and_is_already_played_out(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
    with_bots: list[User],
):
    """
    Бот отыгрывает серию сразу: игрок входит в дуэль, где соперник уже
    ответил. Ждать его нечего, и брошенная партия не подвисает.
    """
    started = await client.post("/api/duels/bot", headers=auth_headers)
    assert started.status_code == 201

    code = started.json()["code"]
    assert code is not None

    match = (await db.execute(select(Match).where(Match.code == code))).scalar_one()
    sessions = (
        (await db.execute(select(GameSession).where(GameSession.match_code == match.code)))
        .scalars()
        .all()
    )

    assert len(sessions) == 1
    bot_session = sessions[0]
    assert bot_session.status == SessionStatus.FINISHED
    assert bot_session.rounds_done == match.rounds_total


async def test_bot_answers_near_the_target(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
    with_bots: list[User],
):
    """
    Случайная точка на Земле — это ноль очков в каждом раунде. Бот должен
    попадать в тот же порядок величин, что и человек.
    """
    started = await client.post("/api/duels/bot", headers=auth_headers)
    code = started.json()["code"]

    rounds = (
        (
            await db.execute(
                select(Round)
                .join(GameSession, Round.session_id == GameSession.id)
                .where(GameSession.match_code == code)
            )
        )
        .scalars()
        .all()
    )

    assert rounds
    for round_obj in rounds:
        assert round_obj.distance_km is not None
        # Половина кадра — то, от чего бот отталкивается там, где статистики
        # нет; разброс уводит дальше, но не на другой континент
        assert float(round_obj.distance_km) < 2000


async def test_duel_with_bot_does_not_move_the_rating(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: User,
    zone: LocationZone,
    db: AsyncSession,
    with_bots: list[User],
):
    """Главное ограничение: рейтинг сравнивает людей, а не прогоны против бота."""
    before = registered_user.rating

    started = await client.post("/api/duels/bot", headers=auth_headers)
    code = started.json()["code"]

    entered = await client.post(f"/api/matches/{code}/join", headers=auth_headers)
    assert entered.status_code == 201

    # Игрок ставит точку мимо: даже проиграв боту, рейтинга он не теряет
    await play_through(client, auth_headers, entered.json(), longitude=0.0, latitude=0.0)
    await db.refresh(registered_user)

    assert registered_user.rating == before

    # Дуэль именно досчитана, а не осталась висеть: иначе проверка выше
    # проходила бы сама собой
    match = (await db.execute(select(Match).where(Match.code == code))).scalar_one()
    assert match.rated_at is not None


async def test_bot_stays_out_of_the_player_count(
    client: AsyncClient,
    db: AsyncSession,
    registered_user: User,
    with_bots: list[User],
):
    """Счётчик на сайте обещает живых игроков — он должен их и считать."""
    answer = await client.get("/api/community")

    assert answer.status_code == 200
    assert answer.json()["players"] == 1


async def test_bot_stays_out_of_the_leaderboard(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
    with_bots: list[User],
):
    await client.post("/api/duels/bot", headers=auth_headers)

    board = await client.get("/api/leaderboard", headers=auth_headers)
    assert board.status_code == 200

    names = {row["display_name"] for row in board.json()["entries"]}
    assert names.isdisjoint({spec.display_name for spec in bots_service.BOTS})


async def test_bot_rounds_stay_out_of_the_zone_statistics(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
    with_bots: list[User],
):
    """
    Иначе получилась бы обратная связь: бот считает промах по среднему зоны и
    сам же его портит.
    """
    await client.post("/api/duels/bot", headers=auth_headers)
    await db.refresh(zone)

    assert zone.total_rounds == 0
    assert zone.average_distance is None


async def test_bot_is_named_a_bot_in_the_standings(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    with_bots: list[User],
):
    """Выдавать бота за человека нельзя: клиенту нужно, чем его пометить."""
    started = await client.post("/api/duels/bot", headers=auth_headers)
    code = started.json()["code"]

    room = await client.get(f"/api/matches/{code}", headers=auth_headers)
    assert room.status_code == 200

    standings = room.json()["standings"]
    assert [row["is_bot"] for row in standings] == [True]


async def test_bot_duel_is_refused_when_bots_are_off(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    with_bots: list[User],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(bots_service.settings, "duel_bots_enabled", False)

    answer = await client.post("/api/duels/bot", headers=auth_headers)

    assert answer.status_code == 409


async def test_bot_duel_is_refused_without_bots(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    """Ботов не завели — сервер говорит об этом, а не молча собирает пустую дуэль."""
    answer = await client.post("/api/duels/bot", headers=auth_headers)

    assert answer.status_code == 404


# ─── Геометрия ответа ────────────────────────────────────────────────────


def test_point_at_distance_is_the_inverse_of_haversine():
    """Бот ставит точку, отступив на заданное расстояние, — отступ должен сойтись."""
    for bearing in (0, 45, 137, 270, 359):
        for distance in (0.5, 10.0, 300.0, 2500.0):
            lon, lat = point_at_distance(37.6, 55.75, distance, bearing)

            assert haversine_km(37.6, 55.75, lon, lat) == pytest.approx(distance, abs=0.5)
            assert -180 <= lon <= 180
