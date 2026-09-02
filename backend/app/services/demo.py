"""
Знакомство с игрой без учётной записи.

Пять известных мест и три способа ответа подряд: сначала выбор из шести
названий, потом страна на карте, в конце точка. Это не облегчённая партия, а
экскурсия — человек успевает попробовать всё, чем игра бывает, до того как
решит, заводить ли аккаунт.

Ни одной строки в базе. Раунд обычной партии живёт в таблице `rounds`, и
гостевые строки пришлось бы исключать из таблицы лидеров, счётчика игроков и
истории, а потом ещё и чистить — ровно на этом когда-то и разошлись с гостями.
Здесь хранить нечего: места фиксированы, цель — центр зоны, результат никуда
не идёт. Сервер помнит только правильные ответы, и клиенту они не уезжают до
ответа, как и в настоящем раунде.

Считают очки те же функции, что и в настоящей игре. Экскурсия, которая
показывает свою арифметику, обещала бы одну игру, а приводила в другую.

Места одни и те же у всех и навсегда: это пять пирамид тайлов, которые всегда
лежат в кэше, — снаружи демонстрация стоит дешевле одного настоящего игрока.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.config import settings
from app.exceptions import NotFoundError, ValidationError
from app.models.enums import AnswerMode, RoundStatus
from app.models.location_zone import LocationZone
from app.observability import metrics
from app.schemas.game import CountryChoice, RoundResult, RoundView, ZoneView
from app.services import countries as countries_service
from app.services import tiles, views
from app.services import zones as zones_service
from app.services.scoring import MAX_ROUND_SCORE, country_score, evaluate_guess
from app.utils import country_names
from app.utils.geo import lonlat_to_tile, tile_center, tile_width_km, zoom_for_extent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoPlace:
    """Одно место экскурсии: что показать и чем на это отвечают."""

    #: Имя зоны в каталоге, русское: по нему каталог сходится сам с собой
    zone_name: str
    answer_mode: AnswerMode
    #: Сколько земли в кадре. Кадр самой зоны сильнее: у достопримечательности
    #: он свой, и показывать её в кадре на полсотни километров значит показать
    #: город вокруг неё вместо неё самой
    view_extent_km: float


#: Экскурсия. Порядок важен: три раунда на выбор из шести названий приучают
#: смотреть на снимок, четвёртый добавляет карту, пятый снимает подпорки и
#: спрашивает точку. Каждый следующий режим отличается от предыдущего ровно
#: одним, а не всем сразу.
DEMO_PLACES: tuple[DemoPlace, ...] = (
    DemoPlace("Москва, центр", AnswerMode.CHOICE, 45),
    DemoPlace("Париж", AnswerMode.CHOICE, 45),
    DemoPlace("Нью-Йорк, Манхэттен", AnswerMode.CHOICE, 45),
    DemoPlace("Пирамиды Гизы", AnswerMode.COUNTRY, 45),
    DemoPlace("Лондон", AnswerMode.POINT, 45),
)

#: Сколько раундов в экскурсии. Отдельным именем: число называется игроку на
#: экране, и считать его на месте значит однажды разойтись с этим списком
DEMO_ROUNDS = len(DEMO_PLACES)


@dataclass(frozen=True)
class DemoRound:
    """
    Готовый раунд экскурсии.

    Поля tile_zoom, tile_x и tile_y названы как у настоящего раунда: прокси
    тайлов берёт их по протоколу, и второй реализации перевода локальных
    координат в глобальные нет.
    """

    index: int
    zone_id: int
    answer_mode: AnswerMode
    tile_zoom: int
    tile_x: int
    tile_y: int
    #: Центр показанного тайла — то самое место, которое ищут
    target_lon: float
    target_lat: float
    view_extent_km: Decimal
    #: Код правильной страны. Пусто в раунде про точку: вопрос был не про неё
    country_code: str | None
    #: Варианты режима выбора в порядке сборки. Игроку они уходят перемешанными
    #: заново на каждый запрос
    choices: tuple[str, ...]


#: Собранная экскурсия. Каталог и границы между релизами не меняются, а
#: собирать их на каждого зашедшего — это десяток запросов в PostGIS на
#: каждого посетителя лендинга
_prepared: tuple[DemoRound, ...] | None = None
_lock = asyncio.Lock()


async def rounds(db: AsyncSession) -> tuple[DemoRound, ...]:
    """Собрать экскурсию один раз и дальше отдавать готовую."""
    global _prepared

    if _prepared is not None:
        return _prepared

    async with _lock:
        # Пока ждали замок, соседний запрос мог всё собрать
        if _prepared is None:
            built = [
                await _build(db, index, place) for index, place in enumerate(DEMO_PLACES, start=1)
            ]
            _prepared = tuple(built)
            logger.info("Экскурсия собрана: %s раундов", len(built))

    return _prepared


def forget() -> None:
    """Забыть собранное. Нужно тестам: каталог у каждого из них свой."""
    global _prepared
    _prepared = None


async def started() -> None:
    """
    Отметить, что знакомство начали.

    Вместе с demo_completed это вся воронка: сколько человек нажали «сыграть»
    и сколько дошли до приглашения. Без этих двух чисел непонятно, где именно
    люди уходят — на первом снимке или на карте стран.
    """
    await metrics.count("demo_started")


async def get_round(db: AsyncSession, index: int) -> DemoRound:
    """Раунд экскурсии по номеру, начиная с единицы."""
    prepared = await rounds(db)

    if not 1 <= index <= len(prepared):
        raise NotFoundError(messages.DEMO_ROUND_NOT_FOUND)

    return prepared[index - 1]


def round_view(demo_round: DemoRound, language: str) -> RoundView:
    """
    Раунд глазами гостя.

    Тот же вид, что у настоящего раунда: экран игры разбирает его по
    answer_mode и не знает, что показывает экскурсию. Координат здесь нет,
    правильного ответа тоже, а варианты перемешаны заново — иначе верный
    стоял бы у всех на одном месте, и его можно было бы называть не глядя.
    """
    options = list(demo_round.choices)
    random.shuffle(options)

    return RoundView(
        id=demo_round.index,
        index=demo_round.index,
        status="active",
        view_extent_km=demo_round.view_extent_km,
        max_zoom=tiles.max_local_zoom(demo_round),
        tiles_url=f"/api/demo/rounds/{demo_round.index}/tiles/{{z}}/{{x}}/{{y}}.jpg",
        attribution=settings.satellite_attribution,
        created_at=datetime.now(UTC),
        answer_mode=demo_round.answer_mode,
        choices=[
            CountryChoice(code=code, name=country_names.name_of(code, language) or code)
            for code in options
        ],
        max_score=MAX_ROUND_SCORE,
        # Подсказок здесь нет: экскурсия и так вся подсказка
        hint=None,
        hint_cost=0,
        deadline_at=None,
    )


async def answer(
    db: AsyncSession,
    demo_round: DemoRound,
    point: tuple[float, float] | None,
    country: str | None,
    language: str,
) -> RoundResult:
    """Проверить ответ гостя тем же способом, каким проверяется настоящий."""
    zone = await db.get(LocationZone, demo_round.zone_id)
    if zone is None:
        raise NotFoundError(messages.DEMO_ROUND_NOT_FOUND)

    view = views.zone_view(zone, language)

    result = (
        await _country_result(db, demo_round, country, view, language)
        if demo_round.answer_mode.by_country
        else _point_result(demo_round, point, view)
    )

    # Считаем после проверки ответа, а не до: отвергнутый запрос — это не
    # пройденное знакомство, и в воронке ему делать нечего
    if demo_round.index == DEMO_ROUNDS:
        await metrics.count("demo_completed")

    return result


def _point_result(
    demo_round: DemoRound, point: tuple[float, float] | None, zone: ZoneView
) -> RoundResult:
    """Раунд про точку: очки за то, насколько близко она поставлена."""
    if point is None:
        raise ValidationError(messages.ANSWER_WITH_PIN)

    longitude, latitude = point
    result = evaluate_guess(
        guess_lon=longitude,
        guess_lat=latitude,
        target_lon=demo_round.target_lon,
        target_lat=demo_round.target_lat,
        view_extent_km=float(demo_round.view_extent_km),
    )

    return _result(
        demo_round,
        zone,
        guess=point,
        distance_km=Decimal(str(result.distance_km)),
        accuracy=Decimal(str(result.accuracy)),
        score=result.score,
        country=None,
        guess_country=None,
    )


async def _country_result(
    db: AsyncSession,
    demo_round: DemoRound,
    code: str | None,
    zone: ZoneView,
    language: str,
) -> RoundResult:
    """
    Раунд про страны: очки за саму страну, а не за расстояние до цели.

    Названный вариант обязан быть одним из показанных: список иначе стал бы
    украшением, ведь запрос собирается и руками, а правильную страну можно
    подобрать перебором всех, минуя шесть предложенных.
    """
    if code is None:
        raise ValidationError(messages.ANSWER_WITH_COUNTRY)

    code = code.upper()

    if demo_round.choices and code not in demo_round.choices:
        raise ValidationError(messages.CHOICE_NOT_OFFERED)

    guessed = await countries_service.by_code(db, code)
    if guessed is None:
        raise ValidationError(messages.NO_SUCH_COUNTRY)

    right = guessed.code == demo_round.country_code
    miss = (
        0.0
        if right
        else await countries_service.distance_km(
            db, guessed.code, demo_round.target_lon, demo_round.target_lat
        )
    )

    return _result(
        demo_round,
        zone,
        guess=None,
        distance_km=Decimal(str(round(miss, 3))),
        # Точки здесь нет вовсе, поэтому нет и точности: вопрос был не про метры
        accuracy=None,
        score=country_score(right, miss),
        country=country_names.name_of(demo_round.country_code or "", language),
        guess_country=country_names.name_of(guessed.code, language) or guessed.name,
    )


def _result(
    demo_round: DemoRound,
    zone: ZoneView,
    *,
    guess: tuple[float, float] | None,
    distance_km: Decimal,
    accuracy: Decimal | None,
    score: int,
    country: str | None,
    guess_country: str | None,
) -> RoundResult:
    """
    Собрать итог в том же виде, в каком его отдаёт настоящий раунд.

    Пустыми остаются ровно те поля, которых у гостя не бывает: время на ответ
    никто не мерил, а идентификатор раунда — это его номер в экскурсии,
    потому что строки в базе за ним не стоит.
    """
    return RoundResult(
        id=demo_round.index,
        index=demo_round.index,
        status=RoundStatus.GUESSED,
        view_extent_km=demo_round.view_extent_km,
        target=(demo_round.target_lon, demo_round.target_lat),
        guess=guess,
        distance_km=distance_km,
        score=score,
        max_score=MAX_ROUND_SCORE,
        accuracy=accuracy,
        country=country,
        guess_country=guess_country,
        answer_seconds=None,
        zone=zone,
        guessed_at=datetime.now(UTC),
    )


async def _build(db: AsyncSession, index: int, place: DemoPlace) -> DemoRound:
    """
    Собрать раунд по месту каталога.

    Цель — центр зоны, а не случайная точка внутри неё: в настоящей партии
    случайность нужна, чтобы один и тот же город каждый раз выглядел
    по-новому, а здесь наоборот — пирамиды обязаны попасть в кадр у всех.
    """
    zone = await zones_service.get_zone_by_name(db, place.zone_name)
    if zone is None:
        raise NotFoundError(messages.DEMO_PLACE_MISSING.format(place=place.zone_name))

    lon, lat = await zones_service.zone_center(db, zone)
    frame_km = float(zone.view_extent_km or place.view_extent_km)

    zoom = zoom_for_extent(lat, frame_km, max_zoom=settings.satellite_max_zoom - 1)
    tile_x, tile_y = lonlat_to_tile(lon, lat, zoom)
    target_lon, target_lat = tile_center(tile_x, tile_y, zoom)

    mode = place.answer_mode
    country_code: str | None = None
    choices: tuple[str, ...] = ()

    if mode.by_country:
        country = await countries_service.at_point(db, target_lon, target_lat)
        if country is None:
            raise NotFoundError(messages.DEMO_PLACE_NOT_FOR_COUNTRIES.format(place=zone.name))

        country_code = country.code

        if mode is AnswerMode.CHOICE:
            options = await countries_service.choices_for(db, country_code, target_lon, target_lat)
            if len(options) < countries_service.CHOICES:
                raise NotFoundError(messages.DEMO_PLACE_NOT_FOR_COUNTRIES.format(place=zone.name))

            choices = tuple(options)

    return DemoRound(
        index=index,
        zone_id=zone.id,
        answer_mode=mode,
        tile_zoom=zoom,
        tile_x=tile_x,
        tile_y=tile_y,
        target_lon=target_lon,
        target_lat=target_lat,
        view_extent_km=Decimal(str(round(tile_width_km(tile_x, tile_y, zoom), 3))),
        country_code=country_code,
        choices=choices,
    )
