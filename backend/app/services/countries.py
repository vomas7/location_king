"""
Страна по точке на карте.

Границы лежат в базе, и отвечает на этот вопрос PostGIS: у него для этого
есть и функция, и индекс. Считать на клиенте нельзя вдвойне — границы весят
мегабайты и вдобавок подсказывают ответ.

Точка может не попасть ни в одну страну: береговая линия в границах упрощена,
и центр приморского города оказывается «в море» на сотни метров. Поэтому
рядом с проверкой на попадание есть поиск ближайшей — с потолком, за которым
океан считается океаном.
"""

import logging

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country import Country

logger = logging.getLogger(__name__)

#: Насколько далеко от берега точка ещё считается «в стране». Тридцать
#: километров покрывают упрощение береговой линии и заодно отмели, но не
#: превращают открытый океан в чью-то территорию
MAX_OFFSHORE_KM = 30


def _point(longitude: float, latitude: float):
    return func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)


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
