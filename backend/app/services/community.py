"""
Сколько людей играет — единственное число, которое игра показывает о себе.

Считается по учётным записям, а не по «активным за сутки»: игроку на первом
экране интересно, есть ли тут вообще кто-то, а не насколько бодро тут было
вчера. Никаких имён и никакой разбивки: это счётчик, а не выгрузка.

Значение кэшируется. Запрос публичный и без авторизации — ограничить его по
игроку нельзя, а считать `count(*)` на каждое открытие страницы незачем:
число меняется медленно, и пятиминутной свежести хватает с запасом.
"""

import logging

from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import redis_client
from app.models.user import User

logger = logging.getLogger(__name__)

CACHE_KEY = "community:players"
CACHE_TTL_SECONDS = 300


async def players(db: AsyncSession) -> int:
    """Сколько всего игроков завело учётную запись."""
    cached = await _cached()
    if cached is not None:
        return cached

    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    await _remember(total)

    return total


async def _cached() -> int | None:
    """Число из кэша. Недоступный Redis не должен ронять первый экран."""
    try:
        stored = await redis_client().get(CACHE_KEY)
    except RedisError as e:
        logger.warning("Кэш счётчика игроков недоступен на чтении: %s", e)
        return None

    if stored is None:
        return None

    try:
        return int(stored)
    except ValueError as e:
        # В ключе лежит не число: чужая запись или ручная правка. Считаем сами
        logger.warning("В кэше счётчика игроков не число: %s", e)
        return None


async def _remember(total: int) -> None:
    """Запомнить число до следующего пересчёта."""
    try:
        await redis_client().set(CACHE_KEY, total, ex=CACHE_TTL_SECONDS)
    except RedisError as e:
        logger.warning("Кэш счётчика игроков недоступен на записи: %s", e)
