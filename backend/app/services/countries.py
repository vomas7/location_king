"""
Страны: определение по точке и контуры для карты догадки.

Полные границы лежат в базе и никуда оттуда не уходят: они весят два
мегабайта, а PostGIS отвечает по ним и точнее, и быстрее, чем это сделал бы
клиент.

Но в режиме стран игрок выбирает страну мышью, и для этого контуры на карте
всё-таки нужны. Никакого ответа они не выдают: на карте лежат границы всех
стран сразу, а какая из них правильная, по ним не узнать. Поэтому наружу
уходит отдельный сильно упрощённый набор — он нужен только чтобы попасть
пальцем, а сверяет ответ всё равно сервер по коду страны.

Точка может не попасть ни в одну страну: береговая линия в границах упрощена,
и центр приморского города оказывается «в море» на сотни метров. Поэтому
рядом с проверкой на попадание есть поиск ближайшей — с потолком, за которым
океан считается океаном.
"""

import json
import logging
import random

from geoalchemy2 import Geography
from redis.exceptions import RedisError
from sqlalchemy import cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import redis_client
from app.models.country import Country

logger = logging.getLogger(__name__)

#: Насколько далеко от берега точка ещё считается «в стране». Тридцать
#: километров покрывают упрощение береговой линии и заодно отмели, но не
#: превращают открытый океан в чью-то территорию
MAX_OFFSHORE_KM = 30


def _point(longitude: float, latitude: float):
    return func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)


#: Сколько вариантов показывать в режиме выбора. Шесть помещаются в два
#: столбца на экране телефона и оставляют осмысленный выбор: из четырёх
#: угадывают наугад слишком часто, из восьми список приходится вычитывать
CHOICES = 6

#: Насколько далеко должны стоять неверные варианты, километров. Соседи по
#: региону сделали бы самый простой режим самым трудным: отличить Ливию от
#: Судана по снимку тяжелее, чем Египет от Норвегии. Тысяча километров
#: разводит варианты по разным местам, и пустыня в кадре сразу отсекает
#: половину списка
CHOICE_FAR_KM = 1000

#: Насколько крупной должна быть страна, чтобы попасть в неверные варианты,
#: квадратных километров. «Бонэйр, Синт-Эстатиус и Саба» — честная строка в
#: списке стран и бессмысленная в списке вариантов: её не выберет никто и
#: никогда, а место в шестёрке она занимает. Пятьдесят тысяч оставляют около
#: полутора сотен стран, которые хотя бы слышали
CHOICE_MIN_KM2 = 50_000

_CHOICES_SQL = text("""
    SELECT code
    FROM countries
    WHERE code <> :correct
      AND ST_Area(border::geography) > :min_area
      AND ST_Distance(
              border::geography,
              ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography
          ) > :far
    ORDER BY random()
    LIMIT :wanted
""")


async def choices_for(
    db: AsyncSession, correct: str, longitude: float, latitude: float
) -> list[str]:
    """
    Варианты ответа для режима выбора: правильный и пять далёких от него.

    Порядок перемешан здесь же: если правильный всегда стоял бы первым, его
    можно было бы выбирать не глядя на снимок.
    """
    others = list(
        (
            await db.execute(
                _CHOICES_SQL,
                {
                    "correct": correct,
                    "longitude": longitude,
                    "latitude": latitude,
                    "far": CHOICE_FAR_KM * 1000,
                    "min_area": CHOICE_MIN_KM2 * 1_000_000,
                    "wanted": CHOICES - 1,
                },
            )
        )
        .scalars()
        .all()
    )

    options = [correct, *others]
    random.shuffle(options)

    return options


async def are_loaded(db: AsyncSession) -> bool:
    """
    Загружены ли границы вообще.

    По ним отсеиваются точки раунда, попавшие в море. Если границ нет, отсеять
    нечем, и раунд собирается как раньше — иначе пустая таблица означала бы,
    что игра не выдаёт ни одного раунда вовсе.
    """
    return (await db.execute(select(Country.code).limit(1))).scalar_one_or_none() is not None


async def at_point(db: AsyncSession, longitude: float, latitude: float) -> Country | None:
    """
    Страна, в которой лежит точка. Ничего — если это открытая вода.

    Сначала проверяется попадание внутрь, и только потом ищется ближайшая:
    иначе точка на границе двух стран доставалась бы то одной, то другой.
    """
    point = _point(longitude, latitude)

    inside = await db.execute(
        select(Country).where(func.ST_Contains(Country.border, point)).limit(1)
    )
    found = inside.scalar_one_or_none()

    if found is not None:
        return found

    # ST_DWithin по географии считает метры по земному шару, а не градусы;
    # сортировка по <-> идёт через тот же индекс, что и проверка попадания
    nearest = await db.execute(
        select(Country)
        .where(
            func.ST_DWithin(
                cast(Country.border, Geography),
                cast(point, Geography),
                MAX_OFFSHORE_KM * 1000,
            )
        )
        .order_by(Country.border.distance_centroid(point))
        .limit(1)
    )
    return nearest.scalar_one_or_none()


async def distance_km(db: AsyncSession, code: str, longitude: float, latitude: float) -> float:
    """
    Сколько километров от точки до границы страны. Внутри страны — ноль.

    По географии, а не по градусам: градус долготы на экваторе и у полярного
    круга — это разные расстояния.
    """
    distance = await db.execute(
        select(
            func.ST_Distance(
                cast(Country.border, Geography),
                cast(_point(longitude, latitude), Geography),
            )
        ).where(Country.code == code)
    )
    meters = distance.scalar_one_or_none()

    return 0.0 if meters is None else float(meters) / 1000


async def by_code(db: AsyncSession, code: str) -> Country | None:
    """Страна по коду ISO."""
    return (await db.execute(select(Country).where(Country.code == code))).scalar_one_or_none()


#: Ключ кэша контуров. Версия в имени: поменяли упрощение — старое значение
#: не подхватится, и не нужно помнить про ручную очистку
OUTLINES_CACHE_KEY = "countries:outlines:v1"

#: Мелкие острова с карты убираем, кроме самого крупного куска страны: в него
#: игрок и целится, а сотня скал по океану весит больше, чем вся Европа.
#: Порог в тысячу квадратных километров — это остров примерно 30 на 30 км
MIN_ISLAND_KM2 = 1000

#: Насколько грубо упрощать контур. Люксембург при допуске большой страны
#: превращается в треугольник, а Россию тонко рисовать незачем: попасть по
#: ней пальцем нетрудно
SIMPLIFY_STEPS = ((50_000, 0.03), (500_000, 0.08))
COARSEST_SIMPLIFY = 0.2

_OUTLINES_SQL = text(
    """
    WITH parts AS (
        SELECT code, name, (ST_Dump(border)).geom AS piece FROM countries
    ), ranked AS (
        SELECT code, name, piece,
               ST_Area(piece::geography) / 1e6 AS km2,
               row_number() OVER (PARTITION BY code ORDER BY ST_Area(piece) DESC) AS rank
        FROM parts
    ), kept AS (
        SELECT code, name, piece
        FROM ranked
        WHERE rank = 1 OR km2 >= CAST(:min_island AS double precision)
    ), sized AS (
        SELECT code, name, piece,
               sum(ST_Area(piece::geography) / 1e6) OVER (PARTITION BY code) AS total
        FROM kept
    )
    SELECT code, name,
           ST_AsGeoJSON(
               ST_Collect(
                   ST_SimplifyPreserveTopology(
                       piece,
                       CASE
                           WHEN total < CAST(:small AS double precision)
                               THEN CAST(:fine AS double precision)
                           WHEN total < CAST(:medium AS double precision)
                               THEN CAST(:middle AS double precision)
                           ELSE CAST(:coarse AS double precision)
                       END
                   )
               ),
               3
           ) AS outline
    FROM sized
    GROUP BY code, name
    ORDER BY code
    """
)


async def outlines(db: AsyncSession) -> str:
    """
    Контуры всех стран одной готовой строкой GeoJSON.

    Строкой, а не структурой: она уходит клиенту как есть и лежит в кэше уже
    собранной. Собирать её на каждый запрос — это перебрать три тысячи
    полигонов ради ответа, который меняется раз в релиз.
    """
    cached = await _cached_outlines()
    if cached is not None:
        return cached

    (small, fine), (medium, middle) = SIMPLIFY_STEPS

    rows = (
        await db.execute(
            _OUTLINES_SQL,
            {
                "min_island": MIN_ISLAND_KM2,
                "small": small,
                "fine": fine,
                "medium": medium,
                "middle": middle,
                "coarse": COARSEST_SIMPLIFY,
            },
        )
    ).all()

    collection = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"code": code, "name": name},
                    "geometry": json.loads(outline),
                }
                for code, name, outline in rows
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    await _cache_outlines(collection)
    logger.info("Контуры стран собраны заново: %s стран", len(rows))

    return collection


async def _cached_outlines() -> str | None:
    """Недоступный Redis не должен ронять режим стран."""
    try:
        cached = await redis_client().get(OUTLINES_CACHE_KEY)
    except RedisError as e:
        logger.warning("Кэш контуров недоступен на чтении: %s", e)
        return None

    return None if cached is None else cached.decode("utf-8")


async def _cache_outlines(collection: str) -> None:
    try:
        await redis_client().set(OUTLINES_CACHE_KEY, collection)
    except RedisError as e:
        logger.warning("Кэш контуров недоступен на записи: %s", e)
