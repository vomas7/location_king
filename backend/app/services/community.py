"""
Сколько людей играет — единственное число, которое игра показывает о себе.

Чисел два, и отвечают они на разные вопросы. Всего игроков — «тут вообще
кто-нибудь есть»; считается по учётным записям, а не по «активным за сутки».
Играют сейчас — «есть ли с кем играть прямо сейчас»; считается по начатым
партиям. Никаких имён и никакой разбивки: это счётчики, а не выгрузка.

Оба кэшируются. Запрос публичный и без авторизации — ограничить его по игроку
нельзя, а считать `count(*)` на каждое открытие страницы незачем. Общее число
меняется медленно, и пятиминутной свежести ему хватает с запасом; число
играющих обещает настоящее время и живёт минуту.
"""

import logging
from datetime import UTC, datetime, timedelta

from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import redis_client
from app.models.enums import SessionStatus
from app.models.game_session import GameSession
from app.models.user import User

logger = logging.getLogger(__name__)

CACHE_KEY = "community:players"
CACHE_TTL_SECONDS = 300

PLAYING_KEY = "community:playing"
#: «Сейчас» живёт минуту: число, которое обещает настоящее время, не должно
#: отставать от него на пять минут, как общий счётчик
PLAYING_TTL_SECONDS = 60

#: Партия, начатая раньше этого, — не «сейчас». Полчаса берётся с запасом:
#: пять раундов по минуте играются быстрее, но человек отходит от экрана
PLAYING_WINDOW = timedelta(minutes=30)


async def players(db: AsyncSession) -> int:
    """
    Сколько всего живых игроков завело учётную запись.

    Соперники-боты — тоже строки в users, но людьми они не являются, и в
    числе, которое игра показывает о себе, им делать нечего.
    """
    cached = await _cached()
    if cached is not None:
        return cached

    total = (
        await db.execute(select(func.count()).select_from(User).where(User.is_bot.is_(False)))
    ).scalar_one()
    await _remember(total)

    return total


async def playing(db: AsyncSession) -> int:
    """
    Сколько человек играет прямо сейчас.

    Это незаконченные партии, начатые меньше получаса назад, — и по одной на
    игрока, а не по одной на партию. Число обещает живых людей за экранами,
    поэтому боты из него исключены: партия бота идёт доли секунды и всё равно
    сюда не попала бы, но полагаться на это нельзя.
    """
    cached = await _cached(PLAYING_KEY)
    if cached is not None:
        return cached

    total = (
        await db.execute(
            select(func.count(func.distinct(GameSession.user_id)))
            .join(User, GameSession.user_id == User.id)
            .where(
                GameSession.status == SessionStatus.ACTIVE,
                GameSession.started_at > datetime.now(UTC) - PLAYING_WINDOW,
                User.is_bot.is_(False),
            )
        )
    ).scalar_one()
    await _remember(total, PLAYING_KEY, PLAYING_TTL_SECONDS)

    return total


async def _cached(key: str = CACHE_KEY) -> int | None:
    """Число из кэша. Недоступный Redis не должен ронять первый экран."""
    try:
        stored = await redis_client().get(key)
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


async def _remember(total: int, key: str = CACHE_KEY, ttl: int = CACHE_TTL_SECONDS) -> None:
    """Запомнить число до следующего пересчёта."""
    try:
        await redis_client().set(key, total, ex=ttl)
    except RedisError as e:
        logger.warning("Кэш счётчика игроков недоступен на записи: %s", e)
