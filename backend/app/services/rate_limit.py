"""
Ограничение частоты запросов.

Счётчики лежат в Redis: INCR с истечением на первом обращении. Окно
фиксированное — на границе окна пропускается до двух лимитов подряд, но для
защиты от перебора паролей и наливания мусора в базу этого достаточно, а
скользящее окно стоило бы отдельной структуры на каждый ключ.

Недоступный Redis не запрещает запросы: игра важнее счётчика. Такие случаи
попадают в лог, чтобы их было видно.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from redis.exceptions import RedisError

from app.exceptions import TooManyRequestsError
from app.observability import metrics
from app.services.tiles import redis_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimit:
    """Сколько запросов и за какое время разрешено с одного ключа."""

    limit: int
    window_seconds: int

    @property
    def description(self) -> str:
        minutes = self.window_seconds // 60
        return f"{self.limit} за {minutes} мин" if minutes else f"{self.limit} за окно"


class Limit(StrEnum):
    """Что именно ограничиваем. Значение попадает в ключ Redis."""

    DELETE_ACCOUNT = "delete-account"
    LOGIN = "login"
    REGISTER = "register"
    RENAME = "rename"
    START_SESSION = "start-session"
    TILES = "tiles"


# Единственная таблица лимитов. Перебор пароля и наливание учёток считаются по
# адресу клиента, игровые запросы — по игроку.
#
# Значения выбраны с оглядкой на общий адрес: за одним NAT сидит целый офис или
# студенческое общежитие, и десяток регистраций за час оттуда — это нормально,
# а не атака. От скрипта такой лимит всё равно защищает: он режет скорость на
# порядки. Настоящая защита от массовой регистрации — подтверждение почты.
RULES: dict[Limit, RateLimit] = {
    Limit.LOGIN: RateLimit(limit=20, window_seconds=15 * 60),
    # Удаление тоже проверяет пароль. Без своего лимита это был бы способ
    # перебирать его в обход лимита на вход: угнанного токена доступа хватило
    # бы, чтобы подбирать пароль без ограничений
    Limit.DELETE_ACCOUNT: RateLimit(limit=5, window_seconds=60 * 60),
    Limit.REGISTER: RateLimit(limit=30, window_seconds=60 * 60),
    # Имя видно другим игрокам. Частая смена — способ запутать соперников в
    # комнате: только что был один игрок, а в таблице уже другой
    Limit.RENAME: RateLimit(limit=10, window_seconds=60 * 60),
    Limit.START_SESSION: RateLimit(limit=60, window_seconds=60 * 60),
    Limit.TILES: RateLimit(limit=3000, window_seconds=60 * 60),
}


async def check(limit: Limit, identity: str) -> None:
    """Учесть запрос и бросить TooManyRequestsError, если лимит исчерпан."""
    rule = RULES[limit]
    key = f"ratelimit:{limit.value}:{identity}"

    try:
        client = redis_client()

        # Счётчик и срок жизни ставятся одной посылкой: раздельными командами
        # ключ мог остаться без срока — например, если соединение оборвалось
        # между ними, — и тогда игрок оказался бы заблокирован навсегда.
        # EXPIRE ... NX не сдвигает срок у уже начатого окна.
        pipeline = client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, rule.window_seconds, nx=True)
        used, _ = await pipeline.execute()

        if used > rule.limit:
            ttl = max(await client.ttl(key), 1)
            metrics.count(f"rate_limited_{limit.value}")
            raise TooManyRequestsError(
                f"Слишком часто. Разрешено {rule.description}, попробуй позже",
                retry_after=ttl,
            )
    except RedisError as e:
        logger.warning("Счётчик лимитов недоступен для %s: %s", key, e)
