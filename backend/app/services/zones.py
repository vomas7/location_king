"""Выбор игровых зон и генерация точки внутри полигона."""

import logging

from sqlalchemy import Select, func, select
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
