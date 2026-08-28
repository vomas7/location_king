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

from app.cache import redis_client
from app.exceptions import TooManyRequestsError
from app.observability import metrics

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
    DUEL_POLL = "duel-poll"
    DUEL_QUEUE = "duel-queue"
    FRIEND_INVITE = "friend-invite"
    FRIEND_MANAGE = "friend-manage"
    HINT = "hint"
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
    # Подсказка пишет в раунд и стоит очков. Больше одной на раунд её всё
    # равно не взять, так что лимит защищает базу от долбёжки, а не игру
    # Заявка в друзья приходит человеку. Перебирать коды в надежде попасть
    # в чужой — это спам, и лимит здесь именно от него
    Limit.FRIEND_INVITE: RateLimit(limit=30, window_seconds=60 * 60),
    # Принять и убрать — ответ на то, что уже есть, поэтому лимит щедрее:
    # он защищает базу от долбёжки, а не игрока от соседа
    Limit.FRIEND_MANAGE: RateLimit(limit=120, window_seconds=60 * 60),
    Limit.HINT: RateLimit(limit=300, window_seconds=60 * 60),
    # Встать в очередь и выйти из неё — редкие действия, а вот опрос идёт
    # раз в три секунды, пока игрок ищет: это до 1200 запросов в час у
    # того, кто ищет непрерывно. Лимит выше с запасом, но не бесконечный
    Limit.DUEL_QUEUE: RateLimit(limit=120, window_seconds=60 * 60),
    Limit.DUEL_POLL: RateLimit(limit=2000, window_seconds=60 * 60),
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
            await metrics.count(f"rate_limited_{limit.value}")
            raise TooManyRequestsError(
                f"Слишком часто. Разрешено {rule.description}, попробуй позже",
                retry_after=ttl,
            )
    except RedisError as e:
        logger.warning("Счётчик лимитов недоступен для %s: %s", key, e)
