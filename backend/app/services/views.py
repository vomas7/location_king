"""
Сборка ответов API из моделей.

Вынесено из роутеров, потому что раунд и сессию отдают три разных эндпоинта, а
правило «до догадки координат в ответе нет» должно быть записано один раз.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.enums import (
    AnswerMode,
    FriendshipStatus,
    RoundStatus,
    SessionStatus,
    category_name,
    continent_name,
)
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.match import Match
from app.models.round import Round
from app.models.user import User
from app.schemas.auth import AvatarView
from app.schemas.daily import DailyResult
from app.schemas.friend import FriendView
from app.schemas.game import (
    CountryChoice,
    GuessResponse,
    HintView,
    RoundResult,
    RoundView,
    SessionSummary,
    SessionView,
    ZoneView,
)
from app.schemas.leaderboard import LeaderboardEntry
from app.schemas.match import MatchStanding, MatchSummary, MatchView
from app.services import friends, tiles
from app.services import game as game_service
from app.services import hints as hints_service
from app.services.leaderboard import LeaderboardRow
from app.services.scoring import score_after_hint
from app.utils import country_names, zone_names


def zone_view(zone: LocationZone, language: str) -> ZoneView:
    """
    Публичное представление зоны на языке игрока.

    Каталог написан по-русски, и русское имя остаётся первичным: по нему зона
    ищется и по нему сходятся границы. Игроку название переводится — «Бангкок»
    кириллицей англоязычному не говорит ничего. Описание не переводится: его
    не показывают, оно для того, кто правит каталог.
    """
    return ZoneView(
        id=zone.id,
        name=zone_names.place_name(zone.name, language) or zone.name,
        description=zone.description,
        category=zone.category,
        category_name=category_name(zone.category, language),
        continent=zone.continent,
        continent_name=continent_name(zone.continent, language),
        country=zone_names.country_name(zone.country, language),
        region=zone_names.place_name(zone.region, language),
        tags=zone.tag_list,
        total_rounds=zone.total_rounds,
        average_distance=zone.average_distance,
    )


def answer_mode_of(round_obj: Round) -> AnswerMode:
    """
    Чем отвечают на раунд. Выводится из самого раунда, а не из условий партии:
    условия остались у серии, а раунд игрока о них уже не знает.
    """
    if round_obj.country_code is None:
        return AnswerMode.POINT

    return AnswerMode.CHOICE if round_obj.choices else AnswerMode.COUNTRY


def choice_names(round_obj: Round, language: str) -> list[tuple[str, str]]:
    """
    Варианты ответа с названиями, в том же порядке, что записан у раунда.

    Порядок перемешан при сборке серии и с тех пор не меняется: иначе список
    прыгал бы при каждой перезагрузке страницы, а у соперника в комнате
    оказался бы своим.

    Названия берутся из таблицы, а не из базы: в базе лежит одно имя, русское,
    а игроку страна называется на его языке.
    """
    if not round_obj.choices:
        return []

    return [
        (code, country_names.name_of(code, language) or code)
        for code in round_obj.choices.split(",")
    ]


async def round_view(db: AsyncSession, round_obj: Round, language: str) -> RoundView:
    """
    Активный раунд: адрес прокси тайлов вместо координат.

    Подсказка собирается заново на каждый ответ — так она переживает
    перезагрузку страницы, а хранить её текст рядом с раундом не приходится.
    Цена нужна и до того, как подсказку взяли: игрок должен знать, что платит,
    а нулевая цена означает, что раскрывать нечего и предлагать её не надо.
    """
    available = await hints_service.for_round(db, round_obj, language)
    taken = round_obj.hint_used
    choices = choice_names(round_obj, language)

    return RoundView(
        id=round_obj.id,
        index=round_obj.position,
        status=round_obj.status,
        view_extent_km=round_obj.view_extent_km,
        max_zoom=tiles.max_local_zoom(round_obj),
        tiles_url=f"/api/rounds/{round_obj.id}/tiles/{{z}}/{{x}}/{{y}}.jpg",
        attribution=settings.satellite_attribution,
        created_at=round_obj.created_at,
        answer_mode=answer_mode_of(round_obj),
        choices=[CountryChoice(code=code, name=name) for code, name in choices],
        max_score=round_obj.max_score,
        hint=(
            HintView(label=available.label, value=available.value)
            if taken and available is not None
            else None
        ),
        hint_cost=(
            0
            if taken or available is None
            else round_obj.max_score - score_after_hint(round_obj.max_score)
        ),
        deadline_at=round_obj.deadline_at,
    )


async def guess_response(
    db: AsyncSession,
    finished: Round,
    session: GameSession,
    next_round: Round | None,
    language: str,
) -> GuessResponse:
    """
    Ответ на закрытый раунд: результат, партия и следующий раунд.

    Одинаковый и для догадки, и для истёкшего времени: раунд закрывается
    по-разному, а показать после этого нужно одно и то же.
    """
    return GuessResponse(
        result=await round_result(db, finished, language),
        session=session_view(session),
        next_round=(await round_view(db, next_round, language) if next_round is not None else None),
        is_session_finished=not session.is_active,
    )


async def round_result(db: AsyncSession, round_obj: Round, language: str) -> RoundResult:
    """Завершённый раунд вместе с координатами цели."""
    target = await game_service.target_coordinates(db, round_obj)
    guess = await game_service.guess_coordinates(db, round_obj)

    return RoundResult(
        id=round_obj.id,
        index=round_obj.position,
        status=round_obj.status,
        view_extent_km=round_obj.view_extent_km,
        target=target,
        guess=guess,
        distance_km=round_obj.distance_km,
        score=round_obj.score,
        max_score=round_obj.max_score,
        accuracy=round_obj.accuracy_percentage,
        country=country_names.name_of(round_obj.country_code, language),
        guess_country=country_names.name_of(round_obj.guess_country_code, language),
        answer_seconds=round_obj.answer_seconds,
        zone=zone_view(round_obj.zone, language),
        guessed_at=round_obj.guessed_at,
    )


def session_view(session: GameSession) -> SessionView:
    """Состояние партии."""
    return SessionView(
        id=session.id,
        status=session.status,
        challenge_day=session.challenge_day,
        rounds_total=session.rounds_total,
        rounds_done=session.rounds_done,
        total_score=session.total_score,
        average_score=session.average_score,
        time_limit_seconds=session.time_limit_seconds,
        started_at=session.started_at,
        finished_at=session.finished_at,
    )


async def session_results(
    db: AsyncSession, rounds: list[Round], language: str
) -> list[RoundResult]:
    """История завершённых раундов сессии по порядку."""
    # Раунд, закрытый по времени, — тоже часть партии: игрок должен увидеть,
    # где была цель, и почему за него ноль
    played = sorted(
        (item for item in rounds if item.status != RoundStatus.ACTIVE),
        key=lambda item: item.position,
    )
    return [await round_result(db, round_obj, language) for round_obj in played]


def session_summary(session: GameSession) -> SessionSummary:
    """Партия в списке истории."""
    return SessionSummary(
        id=session.id,
        status=session.status,
        challenge_day=session.challenge_day,
        rounds_total=session.rounds_total,
        rounds_done=session.rounds_done,
        total_score=session.total_score,
        started_at=session.started_at,
        finished_at=session.finished_at,
    )


def player_name(session: GameSession) -> str:
    """Как показывать игрока в таблицах: своё имя, иначе логин."""
    return session.user.display_name or session.user.username


def friend_view(connection: "friends.Connection") -> FriendView:
    """
    Связь глазами того, кто её смотрит.

    Чужого идентификатора в ответе нет — только идентификатор самой связи:
    по нему её принимают и убирают, и больше он ни для чего не нужен.
    """
    other = connection.other

    return FriendView(
        id=connection.friendship.id,
        display_name=other.display_name or other.username,
        avatar=avatar_view(other),
        rating=other.rating,
        accepted=connection.friendship.status == FriendshipStatus.ACCEPTED,
        incoming=connection.incoming,
        created_at=connection.friendship.created_at,
    )


def avatar_view(user: User) -> AvatarView:
    """Аватарка игрока для таблиц. Собирается там же, где и для профиля."""
    return AvatarView(**user.avatar)


def leaderboard_entry(row: LeaderboardRow) -> LeaderboardEntry:
    """
    Строка таблицы лидеров.

    Цифры берутся из строки, а не из профиля игрока: профиль знает сумму за
    всё время, а таблица считает только партии, подходящие под выбранные
    условия.
    """
    return LeaderboardEntry(
        rank=row.rank,
        user_id=row.user.id,
        display_name=row.user.display_name or row.user.username,
        avatar=avatar_view(row.user),
        games_played=row.games_played,
        total_rounds=row.total_rounds,
        best_score=row.best_score,
        total_score=row.total_score,
        average_distance=row.average_distance,
        sharp_rounds=row.sharp_rounds,
    )


def session_summary_or_none(session: GameSession | None) -> SessionSummary | None:
    """Партия в списке истории или ничего, если её нет."""
    return None if session is None else session_summary(session)


def daily_result(rank: int, session: GameSession) -> DailyResult:
    """Строка таблицы челленджа дня."""
    return DailyResult(
        rank=rank,
        display_name=player_name(session),
        avatar=avatar_view(session.user),
        total_score=session.total_score,
        finished_at=session.finished_at,
    )


def match_standing(rank: int, session: GameSession, viewer: User) -> MatchStanding:
    """
    Строка таблицы комнаты.

    Идентификатора игрока в ответе нет: клиенту достаточно знать, какая строка
    его собственная.
    """
    return MatchStanding(
        rank=rank,
        display_name=player_name(session),
        avatar=avatar_view(session.user),
        total_score=session.total_score,
        rounds_done=session.rounds_done,
        is_finished=session.status == SessionStatus.FINISHED,
        is_you=session.user_id == viewer.id,
        finished_at=session.finished_at,
    )


def match_view(
    match: Match,
    sessions: list[GameSession],
    viewer: User,
    my_session: GameSession | None,
) -> MatchView:
    """Комната вместе с таблицей результатов."""
    return MatchView(
        code=match.code,
        status=match.status,
        host_name=match.host.display_name or match.host.username,
        is_host=match.host_user_id == viewer.id,
        rounds_total=match.rounds_total,
        time_limit_seconds=match.time_limit_seconds,
        players=len(sessions),
        created_at=match.created_at,
        my_session=session_summary_or_none(my_session),
        standings=[
            match_standing(rank, session, viewer) for rank, session in enumerate(sessions, start=1)
        ],
    )


def match_summary(match: Match, players: int) -> MatchSummary:
    """Комната в списке созданных игроком."""
    return MatchSummary(
        code=match.code,
        status=match.status,
        rounds_total=match.rounds_total,
        players=players,
        created_at=match.created_at,
    )
