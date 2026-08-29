"""Выбор игровых зон и генерация точки внутри полигона."""

import logging

from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.enums import group_countries
from app.models.location_zone import LocationZone

logger = logging.getLogger(__name__)


def _filtered(
    category: str | None,
    continent: str | None,
    country_group: str | None = None,
    difficulty: str | None = None,
) -> Select:
    """Запрос активных зон с общими фильтрами."""
    stmt = select(LocationZone).where(LocationZone.is_active.is_(True))

    # Уровень записан у самой зоны: узнаваемость места из его категории не
    # выводится, и разложить её по категориям однажды уже не получилось
    if difficulty is not None:
        stmt = stmt.where(LocationZone.tier == difficulty)
    if category is not None:
        stmt = stmt.where(LocationZone.category == category)
    if continent is not None:
        stmt = stmt.where(LocationZone.continent == continent)
    if country_group is not None:
        stmt = stmt.where(LocationZone.country.in_(group_countries(country_group)))

    return stmt


async def list_zones(
    db: AsyncSession,
    difficulty: str | None = None,
    category: str | None = None,
    continent: str | None = None,
    country_group: str | None = None,
    limit: int = 200,
) -> list[LocationZone]:
    """Активные зоны с фильтрами по уровню, категории и месту."""
    stmt = _filtered(category, continent, country_group, difficulty)
    stmt = stmt.order_by(LocationZone.name).limit(limit)

    return list((await db.execute(stmt)).scalars().all())


async def get_zone(db: AsyncSession, zone_id: int) -> LocationZone:
    """Зона по id. Неактивная зона считается отсутствующей."""
    stmt = select(LocationZone).where(
        LocationZone.id == zone_id,
        LocationZone.is_active.is_(True),
    )
    zone = (await db.execute(stmt)).scalar_one_or_none()

    if zone is None:
        raise NotFoundError(f"Зона {zone_id} не найдена")
    return zone


async def pick_random_zone(
    db: AsyncSession,
    category: str | None = None,
    continent: str | None = None,
    country_group: str | None = None,
    difficulty: str | None = None,
) -> LocationZone:
    """Случайная активная зона под заданные фильтры."""
    stmt = _filtered(category, continent, country_group, difficulty)
    zone = (await db.execute(stmt.order_by(func.random()).limit(1))).scalar_one_or_none()

    if zone is None:
        raise NotFoundError("Нет активных зон под заданные условия")
    return zone


async def random_point_in_zone(db: AsyncSession, zone: LocationZone) -> tuple[float, float]:
    """
    Случайная точка внутри полигона зоны.

    Считает PostGIS: ST_GeneratePoints возвращает MULTIPOINT, из него берётся
    первая точка.
    """
    point = func.ST_GeometryN(func.ST_GeneratePoints(LocationZone.polygon, 1), 1)
    stmt = select(func.ST_X(point), func.ST_Y(point)).where(LocationZone.id == zone.id)

    row = (await db.execute(stmt)).first()
    if row is None or row[0] is None or row[1] is None:
        raise NotFoundError(f"Не удалось выбрать точку в зоне {zone.id}: полигон пуст")

    return float(row[0]), float(row[1])


#: Насколько близко к центру кадра должна быть суша, долей от его ширины.
#: Проверять «точка стоит на суше» нельзя: тогда из игры выпала бы Венеция,
#: которая целиком стоит в лагуне, — а в её кадре берег виден со всех сторон.
#: Важно не где стоит точка, а попадает ли суша в кадр вообще.
LAND_IN_FRAME = 0.4

#: Длина градуса широты в километрах. По долготе градус короче, и в северных
#: широтах проверка выходит строже задуманного — но ошибается она в сторону
#: берега, а не открытой воды, и это ровно та сторона, которая нужна.
KM_PER_DEGREE = 111.19

#: Сколько точек перебрать внутри зоны. Приморская зона наполовину состоит из
#: воды, и сорока хватает, чтобы найти сушу даже там, где её пятая часть.
LAND_TRIES = 40

#: Одним запросом: сорок отдельных попыток на каждый раунд — это сорок
#: обращений к базе там, где достаточно одного
_ON_LAND_SQL = text("""
    WITH candidate AS (
        SELECT (ST_Dump(ST_GeneratePoints(polygon, :tries))).geom AS point
        FROM location_zones
        WHERE id = :zone_id
    )
    SELECT ST_X(point), ST_Y(point)
    FROM candidate
    WHERE EXISTS (
        SELECT 1 FROM countries WHERE ST_DWithin(border, candidate.point, :near)
    )
    LIMIT 1
""")


async def random_point_with_land(
    db: AsyncSession, zone: LocationZone, view_extent_km: float
) -> tuple[float, float] | None:
    """
    Случайная точка зоны, в кадре которой есть суша. Ничего — если её нет.

    Раньше точка бралась откуда угодно внутри зоны, и приморский город
    выдавал раунды посреди моря: Александрия — это десять километров города и
    столько же Средиземного моря, и каждый третий раунд по ней показывал
    игроку ровную синеву без единого ориентира.

    Проверяется именно кадр, а не сама точка: чем шире вид, тем дальше может
    стоять берег, оставаясь видимым. В кадре на сто километров точка посреди
    залива годится, в кадре на пять — уже нет.

    Сушей считаются границы стран — те же, по которым работает режим стран.
    Море внутрь границ не входит, поэтому отдельной карты суши не нужно.
    """
    near = view_extent_km * LAND_IN_FRAME / KM_PER_DEGREE

    row = (
        await db.execute(_ON_LAND_SQL, {"zone_id": zone.id, "tries": LAND_TRIES, "near": near})
    ).first()

    if row is None or row[0] is None or row[1] is None:
        return None

    return float(row[0]), float(row[1])
