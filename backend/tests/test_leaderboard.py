"""Тесты таблицы лидеров и истории партий."""

from datetime import UTC, datetime

import pytest
from geoalchemy2 import WKTElement
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RoundStatus, SessionStatus
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.models.series import RoundSeries
from app.models.user import User
from app.services.auth import create_token, register


async def make_player(
    db: AsyncSession,
    email: str,
    *,
    best_score: int,
    total_score: int,
    games: int = 3,
    rounds: int = 15,
    average_distance: float | None = 10.0,
    difficulty: str | None = None,
    continent: str | None = None,
    country_group: str | None = None,
) -> User:
    """
    Игрок с уже сыгранными партиями.

    Таблица считает по партиям, а не по цифрам в профиле, поэтому подделать
    профиль недостаточно — нужны настоящие завершённые партии с условиями.
    """
    user = await register(db, email, "password for tests", email.split("@")[0])

    series = RoundSeries(
        difficulty=difficulty,
        continent=continent,
        country_group=country_group,
    )
    db.add(series)
    await db.flush()

    # Раунды и очки раскладываем поровну, а лучшую партию делаем первой:
    # зачёт по лучшей смотрит на очки за раунд, поэтому длины партий равны
    per_game = max(rounds // games, 1)

    for index in range(games):
        best = index == 0
        db.add(
            GameSession(
                user_id=user.id,
                series_id=series.id,
                status=SessionStatus.FINISHED,
                rounds_total=per_game,
                rounds_done=per_game if index > 0 else rounds - per_game * (games - 1),
                total_score=total_score // games,
                average_score=best_score if best else best_score / 2,
                average_distance=average_distance,
                finished_at=datetime.now(UTC),
            )
        )

    await db.flush()
    return user


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(user.id, 'access')}"}


async def test_leaderboard_is_open_without_authorization(client: AsyncClient):
    response = await client.get("/api/leaderboard")

    assert response.status_code == 200
    assert response.json()["me"] is None


async def test_leaderboard_ranks_by_best_game(client: AsyncClient, db: AsyncSession):
    await make_player(db, "silver@example.com", best_score=3000, total_score=9000)
    await make_player(db, "gold@example.com", best_score=4800, total_score=5000)
    await make_player(db, "bronze@example.com", best_score=1000, total_score=1000)

    entries = (await client.get("/api/leaderboard?metric=best")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["gold", "silver", "bronze"]
    assert [e["rank"] for e in entries] == [1, 2, 3]


async def test_leaderboard_ranks_by_total_score(client: AsyncClient, db: AsyncSession):
    await make_player(db, "silver@example.com", best_score=3000, total_score=9000)
    await make_player(db, "gold@example.com", best_score=4800, total_score=5000)

    entries = (await client.get("/api/leaderboard?metric=total")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["silver", "gold"]


async def test_leaderboard_by_accuracy_puts_smallest_miss_first(
    client: AsyncClient,
    db: AsyncSession,
):
    await make_player(db, "far@example.com", best_score=1, total_score=1, average_distance=500.0)
    await make_player(db, "near@example.com", best_score=1, total_score=1, average_distance=2.5)

    entries = (await client.get("/api/leaderboard?metric=accuracy")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["near", "far"]


async def test_accuracy_ranking_ignores_players_with_too_few_rounds(
    client: AsyncClient,
    db: AsyncSession,
):
    await make_player(db, "rookie@example.com", best_score=1, total_score=1, rounds=2)
    await make_player(db, "veteran@example.com", best_score=1, total_score=1, rounds=50)

    entries = (await client.get("/api/leaderboard?metric=accuracy")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["veteran"]


async def test_players_without_games_are_not_listed(client: AsyncClient, registered_user: User):
    assert (await client.get("/api/leaderboard")).json()["entries"] == []


async def test_own_place_is_returned_even_outside_the_top(
    client: AsyncClient,
    db: AsyncSession,
):
    for index in range(5):
        await make_player(
            db,
            f"top{index}@example.com",
            best_score=5000 - index,
            total_score=1000,
        )
    outsider = await make_player(db, "me@example.com", best_score=10, total_score=10)

    body = (await client.get("/api/leaderboard?limit=3", headers=headers_for(outsider))).json()

    assert len(body["entries"]) == 3
    assert body["me"]["display_name"] == "me"
    assert body["me"]["rank"] == 6


async def test_player_without_games_has_no_place(client: AsyncClient, auth_headers: dict):
    """Пока не сыграл ни одной партии — места в таблице нет."""
    body = (await client.get("/api/leaderboard", headers=auth_headers)).json()
    assert body["me"] is None


# ── Зачёты по условиям игры ──────────────────────────────────────────


async def test_level_has_its_own_standings(client: AsyncClient, db: AsyncSession):
    """Мастер хардкора не должен обходить всех в зачёте лёгкого уровня."""
    await make_player(
        db, "hardcore@example.com", best_score=4900, total_score=9000, difficulty="hardcore"
    )
    await make_player(db, "easy@example.com", best_score=1200, total_score=1200, difficulty="easy")

    hardcore = (await client.get("/api/leaderboard?difficulty=hardcore")).json()
    easy = (await client.get("/api/leaderboard?difficulty=easy")).json()

    assert [e["display_name"] for e in hardcore["entries"]] == ["hardcore"]
    assert [e["display_name"] for e in easy["entries"]] == ["easy"]

    # Условия возвращаются в ответе: клиент должен видеть, что ему посчитали
    assert hardcore["difficulty"] == "hardcore"


async def test_country_has_its_own_standings(client: AsyncClient, db: AsyncSession):
    await make_player(
        db, "ru@example.com", best_score=3000, total_score=3000, country_group="russia"
    )
    await make_player(db, "usa@example.com", best_score=4000, total_score=4000, country_group="usa")

    entries = (await client.get("/api/leaderboard?country_group=russia")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["ru"]


async def test_general_standings_include_every_condition(client: AsyncClient, db: AsyncSession):
    """Без фильтра считаются все партии, с какими бы условиями их ни играли."""
    await make_player(db, "one@example.com", best_score=3000, total_score=3000, difficulty="easy")
    await make_player(
        db, "two@example.com", best_score=4000, total_score=4000, difficulty="hardcore"
    )

    entries = (await client.get("/api/leaderboard")).json()["entries"]

    assert {e["display_name"] for e in entries} == {"one", "two"}


async def test_numbers_count_only_matching_games(client: AsyncClient, db: AsyncSession):
    """
    Цифры в строке — по отобранным партиям, а не за всё время.

    Иначе рядом с зачётом хардкора стояла бы сумма очков, набранная на лёгком,
    и таблица врала бы о том, что показывает.
    """
    player = await make_player(
        db, "both@example.com", best_score=1000, total_score=3000, difficulty="easy"
    )
    series = RoundSeries(difficulty="hardcore")
    db.add(series)
    await db.flush()
    db.add(
        GameSession(
            user_id=player.id,
            series_id=series.id,
            status=SessionStatus.FINISHED,
            rounds_total=5,
            rounds_done=5,
            total_score=500,
            average_score=100,
            average_distance=42.0,
            finished_at=datetime.now(UTC),
        )
    )
    await db.flush()

    hardcore = (await client.get("/api/leaderboard?difficulty=hardcore")).json()["entries"][0]
    overall = (await client.get("/api/leaderboard")).json()["entries"][0]

    assert hardcore["total_score"] == 500
    assert hardcore["games_played"] == 1
    assert overall["total_score"] == 3500


async def test_own_place_is_counted_within_the_same_conditions(
    client: AsyncClient,
    db: AsyncSession,
):
    leader = await make_player(
        db, "leader@example.com", best_score=4900, total_score=9000, difficulty="hardcore"
    )
    outsider = await make_player(
        db, "outsider@example.com", best_score=100, total_score=100, difficulty="hardcore"
    )
    # Партия на лёгком уровне не должна двигать место в зачёте хардкора
    await make_player(db, "easy@example.com", best_score=5000, total_score=5000, difficulty="easy")

    body = (
        await client.get(
            "/api/leaderboard?difficulty=hardcore&limit=1", headers=headers_for(outsider)
        )
    ).json()

    assert [e["display_name"] for e in body["entries"]] == [leader.display_name]
    assert body["me"]["rank"] == 2


async def test_invalid_metric_is_rejected(client: AsyncClient):
    assert (await client.get("/api/leaderboard?metric=nonsense")).status_code == 422


@pytest.mark.parametrize("limit", [0, 101])
async def test_limit_is_validated(client: AsyncClient, limit: int):
    assert (await client.get(f"/api/leaderboard?limit={limit}")).status_code == 422


# ── История партий ───────────────────────────────────────────────────


async def test_history_requires_authorization(client: AsyncClient):
    assert (await client.get("/api/sessions")).status_code == 401


async def test_history_is_empty_for_new_player(client: AsyncClient, auth_headers: dict):
    body = (await client.get("/api/sessions", headers=auth_headers)).json()

    assert body == {"sessions": [], "total": 0}


async def test_history_lists_played_sessions(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    for _ in range(2):
        state = await client.post(
            "/api/sessions",
            json={"rounds_total": 1},
            headers=auth_headers,
        )
        round_id = state.json()["current_round"]["id"]
        await client.post(
            f"/api/rounds/{round_id}/guess",
            json={"longitude": 37.6, "latitude": 55.7},
            headers=auth_headers,
        )

    body = (await client.get("/api/sessions", headers=auth_headers)).json()

    assert body["total"] == 2
    assert all(session["status"] == "finished" for session in body["sessions"])


async def test_history_does_not_show_other_players_sessions(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
    zone: LocationZone,
):
    await client.post("/api/sessions", json={"rounds_total": 1}, headers=auth_headers)

    body = (await client.get("/api/sessions", headers=other_user_headers)).json()
    assert body["total"] == 0


# ── Продолжение партии ───────────────────────────────────────────────


async def test_current_session_is_null_when_nothing_started(
    client: AsyncClient,
    auth_headers: dict,
):
    """Отсутствие партии — обычное состояние, а не ошибка."""
    response = await client.get("/api/sessions/current", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() is None


async def test_current_session_returns_unfinished_game(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 3},
        headers=auth_headers,
    )
    session_id = started.json()["session"]["id"]

    body = (await client.get("/api/sessions/current", headers=auth_headers)).json()

    assert body["session"]["id"] == session_id
    assert body["current_round"]["index"] == 1


async def test_current_session_is_gone_after_finish(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    started = await client.post(
        "/api/sessions",
        json={"rounds_total": 1},
        headers=auth_headers,
    )
    session_id = started.json()["session"]["id"]
    await client.post(f"/api/sessions/{session_id}/finish", headers=auth_headers)

    assert (await client.get("/api/sessions/current", headers=auth_headers)).json() is None


async def test_current_session_carries_no_target_coordinates(
    client: AsyncClient,
    auth_headers: dict,
    zone: LocationZone,
):
    await client.post("/api/sessions", json={"rounds_total": 3}, headers=auth_headers)

    body = (await client.get("/api/sessions/current", headers=auth_headers)).text

    assert "target" not in body
    assert zone.name not in body


async def test_current_session_requires_authorization(client: AsyncClient):
    assert (await client.get("/api/sessions/current")).status_code == 401


async def add_rounds(
    db: AsyncSession, user: User, zone: LocationZone, *, sharp: int, weak: int
) -> None:
    """
    Дописать игроку сыгранные раунды: меткие и не очень.

    Меткий — взятый почти в точку: девять десятых максимума и выше. Точность
    это среднее, и один провальный раунд портит её целиком, а меткие раунды
    остаются в зачёте навсегда — поэтому метрики и разные.
    """
    session = GameSession(
        user_id=user.id,
        status=SessionStatus.FINISHED,
        rounds_total=sharp + weak,
        rounds_done=sharp + weak,
        total_score=0,
        finished_at=datetime.now(UTC),
    )
    db.add(session)
    await db.flush()

    point = WKTElement("POINT(37.6 55.75)", srid=4326)

    for index in range(sharp + weak):
        db.add(
            Round(
                session_id=session.id,
                zone_id=zone.id,
                position=index + 1,
                target_point=point,
                tile_zoom=10,
                tile_x=1,
                tile_y=1,
                view_extent_km=45,
                max_score=5000,
                score=5000 if index < sharp else 1000,
                status=RoundStatus.GUESSED,
            )
        )

    await db.flush()


async def test_leaderboard_ranks_by_games_played(client: AsyncClient, db: AsyncSession):
    """Упорство — тоже результат: кто доиграл больше партий, тот и выше."""
    await make_player(db, "many@example.com", best_score=100, total_score=100, games=9, rounds=27)
    await make_player(db, "few@example.com", best_score=5000, total_score=5000, games=2, rounds=6)

    entries = (await client.get("/api/leaderboard?metric=games")).json()["entries"]

    assert [e["display_name"] for e in entries] == ["many", "few"]
    assert [e["games_played"] for e in entries] == [9, 2]


async def test_leaderboard_ranks_by_sharp_rounds(
    client: AsyncClient, db: AsyncSession, zone: LocationZone
):
    """Меткость считает удачные раунды, а не среднее по всем."""
    sniper = await make_player(db, "sniper@example.com", best_score=100, total_score=100, games=1)
    steady = await make_player(db, "steady@example.com", best_score=100, total_score=100, games=1)

    await add_rounds(db, sniper, zone, sharp=4, weak=6)
    await add_rounds(db, steady, zone, sharp=1, weak=1)

    entries = (await client.get("/api/leaderboard?metric=sharp")).json()["entries"]

    assert entries[0]["display_name"] == "sniper"
    assert entries[0]["sharp_rounds"] == 4
    assert entries[1]["sharp_rounds"] == 1


async def test_sharp_rounds_do_not_inflate_the_other_numbers(
    client: AsyncClient, db: AsyncSession, zone: LocationZone
):
    """
    Меткость считается подзапросом, а не соединением с раундами.

    Соединение размножило бы строки партий, и «партий» вместе с «суммой очков»
    выросли бы во столько раз, сколько в партии раундов.
    """
    player = await make_player(
        db, "counted@example.com", best_score=100, total_score=900, games=3, rounds=9
    )
    await add_rounds(db, player, zone, sharp=5, weak=0)

    entry = (await client.get("/api/leaderboard?metric=total")).json()["entries"][0]

    # Три партии из make_player плюс одна с раундами — и ни одной лишней
    assert entry["games_played"] == 4
    assert entry["total_score"] == 900
    assert entry["sharp_rounds"] == 5
