"""
Очередь подбора соперника.

Живёт в Redis, а не в памяти процесса: воркеров четыре, и очередь у каждого
была бы своя — игроки искали бы друг друга и не находили. По той же причине
там же лежат метрики.

Живого соединения нет. Клиент опрашивает сервер раз в несколько секунд, и
каждый опрос заодно продлевает запись в очереди: закрыл вкладку — выпал сам,
и счётчик ищущих не врёт. Это сознательный размен. Вебсокет держал бы воркер
и потребовал бы расширения строгой CSP ради десятка запросов в секунду.

Запись хранится строкой «рейтинг|встал|последний опрос» в одном хэше, а
соперник ищется перебором. При сотне ищущих это сотня коротких строк на
запрос — дешевле, чем отдельный индекс, который пришлось бы чистить отдельно.
"""

import logging
import time
from dataclasses import dataclass

from app.cache import redis_client

logger = logging.getLogger(__name__)

#: Все ищущие сейчас: id игрока → «рейтинг|встал|последний опрос»
QUEUE_KEY = "duel:searching"
#: Найденная пара ждёт игрока здесь, пока он не опросит сервер
FOUND_KEY = "duel:found"
#: Пару подбирают под этим замком: иначе два воркера спарят одного дважды
LOCK_KEY = "duel:lock"

#: Сколько запись живёт без опроса. Клиент опрашивает раз в три секунды,
#: так что четырёх пропущенных опросов достаточно, чтобы считать игрока ушедшим
FRESH_SECONDS = 12

#: Сколько найденная пара ждёт, пока игрок за ней придёт
FOUND_TTL_SECONDS = 120

#: Замок держится секунды: он нужен только на время подбора
LOCK_TTL_SECONDS = 5

#: Насколько рейтинги могут расходиться в начале поиска и насколько полоса
#: расширяется с каждым десятком секунд ожидания
BAND_START = 50
BAND_STEP = 25
BAND_EVERY_SECONDS = 10

#: После этого берём кого угодно: ждать соперника ровно своего уровня
#: интереснее в теории, чем на практике
OPEN_AFTER_SECONDS = 120


@dataclass(frozen=True)
class Searcher:
    """Игрок в очереди."""

    user_id: int
    rating: int
    joined_at: float
    seen_at: float

    def waited(self, now: float) -> float:
        return max(now - self.joined_at, 0.0)

    def band(self, now: float) -> float:
        """Насколько далёкий по рейтингу соперник его сейчас устроит."""
        waited = self.waited(now)
        if waited >= OPEN_AFTER_SECONDS:
            return float("inf")
        return BAND_START + BAND_STEP * int(waited // BAND_EVERY_SECONDS)


def _encode(searcher: Searcher) -> str:
    return f"{searcher.rating}|{searcher.joined_at}|{searcher.seen_at}"


def _decode(user_id: str, raw: str) -> Searcher | None:
    """Запись очереди. Мусор в ней — данные, а не сбой: просто выкидываем."""
    parts = raw.split("|")
    if len(parts) != 3:
        return None

    try:
        return Searcher(
            user_id=int(user_id),
            rating=int(parts[0]),
            joined_at=float(parts[1]),
            seen_at=float(parts[2]),
        )
    except ValueError:
        logger.warning("Не разобрал запись очереди для %s: %r", user_id, raw)
        return None


async def join(user_id: int, rating: int) -> bool:
    """
    Встать в очередь или продлить запись. False — вставать уже незачем.

    Момент, когда игрок встал, сохраняется: от него считается, насколько
    широко искать соперника.

    Того, кому пара уже нашлась, очередь не принимает. Иначе он остался бы в
    ней до истечения записи и мог бы получить вторую дуэль, в которую никогда
    не войдёт, — а соперник по ней десять минут ждал бы победы над пустотой.
    """
    now = time.time()
    client = redis_client()

    if await client.exists(f"{FOUND_KEY}:{user_id}"):
        return False

    existing = await client.hget(QUEUE_KEY, str(user_id))
    joined_at = now

    if existing is not None:
        previous = _decode(str(user_id), existing.decode())
        if previous is not None and now - previous.seen_at <= FRESH_SECONDS:
            joined_at = previous.joined_at

    searcher = Searcher(user_id=user_id, rating=rating, joined_at=joined_at, seen_at=now)
    await client.hset(QUEUE_KEY, str(user_id), _encode(searcher))

    return True


async def leave(user_id: int) -> None:
    """Выйти из очереди."""
    await redis_client().hdel(QUEUE_KEY, str(user_id))


async def searching(now: float | None = None) -> list[Searcher]:
    """
    Кто ищет прямо сейчас.

    Записи тех, кто перестал опрашивать, удаляются здесь же: отдельная уборка
    по расписанию ради этого не нужна, а счётчик у кнопки должен быть честным.
    """
    moment = time.time() if now is None else now
    client = redis_client()

    raw = await client.hgetall(QUEUE_KEY)
    alive: list[Searcher] = []
    stale: list[str] = []

    for key, value in raw.items():
        user_id = key.decode()
        searcher = _decode(user_id, value.decode())

        if searcher is None or moment - searcher.seen_at > FRESH_SECONDS:
            stale.append(user_id)
            continue
        alive.append(searcher)

    if stale:
        await client.hdel(QUEUE_KEY, *stale)

    return alive


def pick_opponent(seeker: Searcher, others: list[Searcher], now: float) -> Searcher | None:
    """
    Кто из очереди подходит игроку.

    Полоса берётся шире из двух: тот, кто ждёт дольше, тянет пару к себе —
    иначе долго ждущий так и не дождётся никого, пока рядом кто-то только
    что встал.
    """
    candidates = [
        other
        for other in others
        if other.user_id != seeker.user_id
        and abs(other.rating - seeker.rating) <= max(seeker.band(now), other.band(now))
    ]

    if not candidates:
        return None

    # Из подходящих — ближайший по рейтингу: дуэль тем интереснее, чем ровнее
    return min(candidates, key=lambda other: abs(other.rating - seeker.rating))


async def lock() -> bool:
    """Взять замок на подбор. False — прямо сейчас подбирает кто-то другой."""
    taken = await redis_client().set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL_SECONDS)
    return bool(taken)


async def unlock() -> None:
    await redis_client().delete(LOCK_KEY)


async def announce(user_ids: tuple[int, ...], code: str) -> None:
    """Сказать обоим, что пара нашлась, и убрать их из очереди."""
    client = redis_client()
    pipeline = client.pipeline()

    for user_id in user_ids:
        pipeline.set(f"{FOUND_KEY}:{user_id}", code, ex=FOUND_TTL_SECONDS)

    pipeline.hdel(QUEUE_KEY, *(str(user_id) for user_id in user_ids))
    await pipeline.execute()


async def take_found(user_id: int) -> str | None:
    """Забрать найденную пару. Второй раз она уже не вернётся."""
    client = redis_client()
    key = f"{FOUND_KEY}:{user_id}"

    pipeline = client.pipeline()
    pipeline.get(key)
    pipeline.delete(key)
    code, _ = await pipeline.execute()

    # Клиент Redis отдаёт байты: он общий на всё приложение и настроен так же
    # для тайлов, которые байтами и являются
    return None if code is None else code.decode()
