"""
Дуэли: подбор соперника и рейтинг.

Рейтинг — единственное число в игре, которое сравнивает игроков между собой,
поэтому проверяется и арифметика, и то, что его нельзя начислить дважды или
получить, закрыв вкладку.
"""

import time
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MatchKind, SessionStatus
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.match import Match
from app.models.user import User
from app.services import duels, matchmaking
from app.services.auth import create_token, register
from app.utils import elo
from tests.helpers import play_through

# ─── Арифметика рейтинга ─────────────────────────────────────────────────


def test_winner_gains_what_loser_loses():
    """Рейтинг перетекает, а не появляется: иначе он поплыл бы вверх у всех."""
    winner = elo.updated(1200, 1200, 1.0, 50)
    loser = elo.updated(1200, 1200, 0.0, 50)

    assert winner - 1200 == 1200 - loser


def test_beating_a_stronger_player_is_worth_more():
    over_stronger = elo.updated(1000, 1400, 1.0, 50) - 1000
    over_weaker = elo.updated(1400, 1000, 1.0, 50) - 1400

    assert over_stronger > over_weaker


def test_newcomer_moves_faster():
    """Первые дуэли двигают рейтинг сильнее: новичку нужно найти своё место."""
    novice = elo.updated(1000, 1000, 1.0, 0) - 1000
    veteran = elo.updated(1000, 1000, 1.0, elo.PLACEMENT_DUELS) - 1000

    assert novice > veteran


def test_draw_between_equals_changes_nothing():
    assert elo.updated(1000, 1000, 0.5, 0) == 1000


def test_rating_has_a_floor():
    rating = elo.MIN_RATING
    for _ in range(20):
        rating = elo.updated(rating, 2000, 0.0, 50)

    assert rating == elo.MIN_RATING


def test_impossible_outcome_is_rejected():
    with pytest.raises(ValueError):
        elo.updated(1000, 1000, 1.5, 0)


# ─── Очередь ─────────────────────────────────────────────────────────────


def searcher(user_id: int, rating: int, waited: float, now: float) -> matchmaking.Searcher:
    return matchmaking.Searcher(
        user_id=user_id,
        rating=rating,
        joined_at=now - waited,
        seen_at=now,
    )


def test_band_widens_while_waiting():
    now = time.time()
    just_joined = searcher(1, 1000, waited=0, now=now)
    waiting = searcher(2, 1000, waited=60, now=now)

    assert just_joined.band(now) == matchmaking.BAND_START
    assert waiting.band(now) > just_joined.band(now)


def test_long_wait_accepts_anyone():
    now = time.time()
    forever = searcher(1, 1000, waited=matchmaking.OPEN_AFTER_SECONDS + 1, now=now)

    assert forever.band(now) == float("inf")


def test_opponent_must_be_close_by_rating():
    now = time.time()
    seeker = searcher(1, 1000, waited=0, now=now)
    far = searcher(2, 1900, waited=0, now=now)

    assert matchmaking.pick_opponent(seeker, [seeker, far], now) is None


def test_the_one_who_waits_longer_pulls_the_pair():
    """Иначе долго ждущий не дождётся никого: рядом всё время кто-то новый."""
    now = time.time()
    seeker = searcher(1, 1000, waited=0, now=now)
    patient = searcher(2, 1300, waited=matchmaking.OPEN_AFTER_SECONDS + 1, now=now)

    found = matchmaking.pick_opponent(seeker, [seeker, patient], now)

    assert found is not None
    assert found.user_id == 2


def test_closest_rating_wins():
    now = time.time()
    seeker = searcher(1, 1000, waited=0, now=now)
    near = searcher(2, 1020, waited=0, now=now)
    farther = searcher(3, 1045, waited=0, now=now)

    found = matchmaking.pick_opponent(seeker, [seeker, near, farther], now)

    assert found is not None
    assert found.user_id == 2


async def test_queue_forgets_those_who_stopped_asking():
    """Счётчик у кнопки должен быть честным: закрыл вкладку — выпал."""
    await matchmaking.join(1, 1000)

    assert len(await matchmaking.searching()) == 1

    later = time.time() + matchmaking.FRESH_SECONDS + 1
    assert await matchmaking.searching(later) == []


async def test_rejoining_keeps_the_original_wait():
    """Опрос продлевает запись, но не обнуляет ожидание — иначе полоса
    поиска никогда не расширится."""
    await matchmaking.join(1, 1000)
    first = (await matchmaking.searching())[0]

    await matchmaking.join(1, 1000)
    second = (await matchmaking.searching())[0]

    assert second.joined_at == first.joined_at


# ─── Подбор через API ────────────────────────────────────────────────────


@pytest.fixture
async def rival(db: AsyncSession) -> User:
    """Второй игрок, которому есть с кем играть."""
    user = await register(db, "rival@example.com", "another long password", "Соперник")
    await db.flush()
    return user


@pytest.fixture
def rival_headers(rival: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(rival.id, 'access')}"}


async def test_alone_in_the_queue_you_just_wait(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    entered = await client.post("/api/duels/queue", headers=auth_headers)
    assert entered.status_code == 201
    assert entered.json() == {"searching": 1, "code": None}

    polled = await client.post("/api/duels/queue/poll", headers=auth_headers)
    assert polled.json() == {"searching": 1, "code": None}


async def test_two_players_are_paired(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
):
    await client.post("/api/duels/queue", headers=auth_headers)
    await client.post("/api/duels/queue", headers=rival_headers)

    # Пару находит тот, кто спросил первым, второй забирает готовый код
    first = (await client.post("/api/duels/queue/poll", headers=auth_headers)).json()
    assert first["code"] is not None

    second = (await client.post("/api/duels/queue/poll", headers=rival_headers)).json()
    assert second["code"] == first["code"]

    match = (await db.execute(select(Match).where(Match.code == first["code"]))).scalar_one()
    assert match.kind == MatchKind.DUEL
    assert match.rounds_total == duels.ROUNDS_TOTAL
    assert match.time_limit_seconds == duels.TIME_LIMIT_SECONDS


async def test_paired_players_leave_the_queue(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
    zone: LocationZone,
):
    await client.post("/api/duels/queue", headers=auth_headers)
    await client.post("/api/duels/queue", headers=rival_headers)
    await client.post("/api/duels/queue/poll", headers=auth_headers)

    assert await matchmaking.searching() == []


async def test_leaving_the_queue_stops_the_search(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    await client.post("/api/duels/queue", headers=auth_headers)

    dropped = await client.delete("/api/duels/queue", headers=auth_headers)
    assert dropped.status_code == 204

    assert await matchmaking.searching() == []


async def test_duel_format_is_published(client: AsyncClient, auth_headers: dict):
    """Условия дуэли решает сервер, и клиент их не пересказывает."""
    body = (await client.get("/api/duels/format")).json()

    assert body["rounds_total"] == duels.ROUNDS_TOTAL
    assert body["time_limit_seconds"] == duels.TIME_LIMIT_SECONDS
    assert body["difficulty"] == duels.DIFFICULTY


# ─── Рейтинг по итогу ────────────────────────────────────────────────────


async def play_duel(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
) -> str:
    """Свести двоих в дуэли и вернуть её код."""
    await client.post("/api/duels/queue", headers=auth_headers)
    await client.post("/api/duels/queue", headers=rival_headers)

    found = (await client.post("/api/duels/queue/poll", headers=auth_headers)).json()
    code = found["code"]
    assert code is not None

    return code


async def join_duel(client: AsyncClient, headers: dict, code: str) -> dict:
    entered = await client.post(f"/api/matches/{code}/join", headers=headers)
    assert entered.status_code == 201, entered.text
    return entered.json()


async def test_winner_gains_rating_and_loser_gives_it_away(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
    registered_user: User,
    rival: User,
    zone: LocationZone,
    db: AsyncSession,
):
    code = await play_duel(client, auth_headers, rival_headers)

    mine = await join_duel(client, auth_headers, code)
    theirs = await join_duel(client, rival_headers, code)

    await play_through(client, auth_headers, mine)
    # Соперник тычет в другое полушарие
    await play_through(client, rival_headers, theirs, longitude=-70.0, latitude=-30.0)

    await db.refresh(registered_user)
    await db.refresh(rival)

    assert registered_user.duels_played == rival.duels_played == 1
    assert registered_user.rating > elo.START_RATING
    assert rival.rating < elo.START_RATING
    assert registered_user.rating - elo.START_RATING == elo.START_RATING - rival.rating

    match = (await db.execute(select(Match).where(Match.code == code))).scalar_one()
    assert match.rated_at is not None


async def test_equal_scores_are_a_draw(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
    registered_user: User,
    rival: User,
    zone: LocationZone,
    db: AsyncSession,
):
    """
    Ничья не двигает рейтинг равных соперников.

    Счёт проставляется руками, а не доигрыванием: в дуэли есть таймер, и два
    одинаковых ответа дают чуть разные очки — тот, кто ответил на полсекунды
    быстрее, получает больше. Ровную ничью так не поймать.
    """
    code = await play_duel(client, auth_headers, rival_headers)
    await join_duel(client, auth_headers, code)
    await join_duel(client, rival_headers, code)

    sessions = (
        (await db.execute(select(GameSession).where(GameSession.match_code == code)))
        .scalars()
        .all()
    )
    for session in sessions:
        session.status = SessionStatus.FINISHED
        session.total_score = 4200
    await db.flush()

    match = (await db.execute(select(Match).where(Match.code == code))).scalar_one()
    assert await duels.settle(db, match) is True

    await db.refresh(registered_user)
    await db.refresh(rival)

    assert registered_user.rating == rival.rating == elo.START_RATING
    assert registered_user.duels_played == rival.duels_played == 1


async def test_rating_is_not_awarded_twice(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
    registered_user: User,
    zone: LocationZone,
    db: AsyncSession,
):
    code = await play_duel(client, auth_headers, rival_headers)

    mine = await join_duel(client, auth_headers, code)
    theirs = await join_duel(client, rival_headers, code)
    await play_through(client, auth_headers, mine)
    await play_through(client, rival_headers, theirs)

    match = (await db.execute(select(Match).where(Match.code == code))).scalar_one()
    rated_at = match.rated_at

    assert await duels.settle(db, match) is False
    await db.refresh(match)
    assert match.rated_at == rated_at


async def test_abandoned_duel_goes_to_the_one_who_finished(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
    registered_user: User,
    rival: User,
    zone: LocationZone,
    db: AsyncSession,
):
    """Иначе рейтинг чинился бы закрытием вкладки."""
    code = await play_duel(client, auth_headers, rival_headers)

    mine = await join_duel(client, auth_headers, code)
    await join_duel(client, rival_headers, code)
    await play_through(client, auth_headers, mine)

    match = (await db.execute(select(Match).where(Match.code == code))).scalar_one()
    assert match.rated_at is None, "соперник ещё может вернуться"

    # Время вышло — соперник не вернулся
    match.created_at = datetime.now(UTC) - duels.ABANDON_AFTER - timedelta(minutes=1)
    await db.flush()

    assert await duels.settle_stale(db) == 1

    await db.refresh(registered_user)
    await db.refresh(rival)

    assert registered_user.rating > elo.START_RATING
    assert rival.rating < elo.START_RATING


async def test_unfinished_duel_blocks_a_new_search(
    client: AsyncClient,
    auth_headers: dict,
    rival_headers: dict,
    zone: LocationZone,
):
    """Бросить дуэль ради новой — значит подарить сопернику пустое ожидание."""
    code = await play_duel(client, auth_headers, rival_headers)
    await join_duel(client, auth_headers, code)

    again = await client.post("/api/duels/queue", headers=auth_headers)

    assert again.status_code == 409


async def test_room_is_not_a_duel(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
    db: AsyncSession,
):
    """Рейтинг меняют только дуэли: комнату с друзьями легко подстроить."""
    created = await client.post(
        "/api/matches",
        json={"rounds_total": 1, "view_extent_km": 15.0},
        headers=auth_headers,
    )
    assert created.status_code == 201

    match = (
        await db.execute(select(Match).where(Match.code == created.json()["code"]))
    ).scalar_one()

    assert match.kind == MatchKind.ROOM
    assert await duels.settle(db, match) is False
