"""
Прокси тайлов спутниковых снимков.

Клиент не знает, где находится цель, поэтому тайлы он запрашивает по локальным
координатам внутри раунда. Сервер переводит их в глобальные, тянет снимок у
провайдера и кэширует в Redis.

Локальная сетка раунда — это квадродерево с корнем в тайле раунда: локальный
уровень z содержит 2^z × 2^z тайлов, и каждый из них ровно совпадает с тайлом
провайдера на зуме tile_zoom + z. Поэтому картинку не нужно резать или
пересобирать, а выйти за пределы показанной области клиент не может.
"""

import asyncio
import hashlib
import logging

import httpx
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.exceptions import NotFoundError, UpstreamError
from app.models.round import Round
from app.observability import metrics

logger = logging.getLogger(__name__)

TILE_CONTENT_TYPE = "image/jpeg"

# Сколько уровней зума вглубь доступно игроку от тайла раунда.
# Больше уровней — детальнее снимок и тяжелее прокси.
MAX_LOCAL_ZOOM = 4

_http_client: httpx.AsyncClient | None = None
_redis_client: Redis | None = None

# Разные шаблоны провайдера не должны делить кэш
_provider_key = hashlib.sha256(settings.satellite_tile_url.encode()).hexdigest()[:8]


def _get_http_client() -> httpx.AsyncClient:
    global _http_client

    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=settings.tile_request_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "LocationKing/1.0 (+https://github.com/vomas7/location_king)"},
        )
    return _http_client


def redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url)
    return _redis_client


def max_local_zoom(round_obj: Round) -> int:
    """До какого локального зума игрок может приблизить снимок."""
    return max(0, min(MAX_LOCAL_ZOOM, settings.satellite_max_zoom - round_obj.tile_zoom))


def local_to_source_tile(round_obj: Round, z: int, x: int, y: int) -> tuple[int, int, int]:
    """Перевести локальные координаты тайла раунда в координаты провайдера."""
    limit = max_local_zoom(round_obj)

    if not 0 <= z <= limit:
        raise NotFoundError(f"Уровень {z} за пределами раунда")

    side = 2**z
    if not (0 <= x < side and 0 <= y < side):
        raise NotFoundError(f"Тайл {x}/{y} за пределами раунда")

    return (
        round_obj.tile_zoom + z,
        round_obj.tile_x * side + x,
        round_obj.tile_y * side + y,
    )


async def get_tile(round_obj: Round, z: int, x: int, y: int) -> bytes:
    """Вернуть тайл раунда: из кэша, иначе от провайдера."""
    source_z, source_x, source_y = local_to_source_tile(round_obj, z, x, y)
    cache_key = f"tile:{_provider_key}:{source_z}:{source_x}:{source_y}"

    cached = await cache_get(cache_key)
    if cached is not None:
        metrics.count("tile_cache_hit")
        return cached

    metrics.count("tile_cache_miss")

    url = settings.satellite_tile_url.format(z=source_z, x=source_x, y=source_y)

    try:
        response = await _get_http_client().get(url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Провайдер снимков не отдал тайл %s: %s", url, e)
        raise UpstreamError("Провайдер снимков недоступен") from e

    tile = response.content
    content_type = response.headers.get("content-type", "")

    # Провайдер может ответить двухсоткой и страницей с ошибкой. Положив её в
    # кэш, мы бы неделю отдавали игроку HTML под видом снимка.
    if not content_type.startswith("image/") or not tile:
        logger.error("Провайдер снимков вернул не картинку (%s) для %s", content_type, url)
        raise UpstreamError("Провайдер снимков вернул не картинку")

    await cache_set(cache_key, tile)
    return tile


async def prewarm(round_obj: Round) -> None:
    """
    Заранее сходить за верхними тайлами раунда.

    Первый тайл игрок ждёт живьём, пока сервер ходит к провайдеру — это
    заметная пауза в начале раунда. Прогрев снимает её для самого первого
    экрана; остальные тайлы подтянутся по ходу.
    """
    # Нулевой уровень — весь участок целиком, первый — те же четыре четверти
    # покрупнее. Дальше игрок приближает сам, и там уже работает кэш.
    levels = range(min(1, max_local_zoom(round_obj)) + 1)
    coordinates = [(z, x, y) for z in levels for x in range(2**z) for y in range(2**z)]

    async def fetch(z: int, x: int, y: int) -> None:
        try:
            await get_tile(round_obj, z, x, y)
        except (NotFoundError, UpstreamError) as e:
            # Прогрев — необязательная оптимизация: не вышло, значит игрок
            # подождёт как раньше
            logger.debug("Прогрев тайла %s/%s/%s не удался: %s", z, x, y, e)

    await asyncio.gather(*(fetch(z, x, y) for z, x, y in coordinates))


def schedule_prewarm(round_obj: Round) -> None:
    """Запустить прогрев в фоне, не задерживая ответ игроку."""
    if not settings.tile_prewarm:
        return

    task = asyncio.create_task(prewarm(round_obj))

    # Ссылку нужно держать, иначе сборщик мусора может убить задачу на полпути
    _background.add(task)
    task.add_done_callback(_background.discard)


_background: set[asyncio.Task[None]] = set()


async def cache_get(key: str) -> bytes | None:
    """
    Достать тайл из кэша.

    Вместе с cache_set образует единственный шов между прокси и хранилищем:
    через него же тесты подставляют кэш в памяти.
    Недоступный Redis не должен ронять игру.
    """
    try:
        return await redis_client().get(key)
    except RedisError as e:
        logger.warning("Кэш тайлов недоступен на чтении: %s", e)
        return None


async def cache_set(key: str, tile: bytes) -> None:
    """Положить тайл в кэш. Недоступный Redis не должен ронять игру."""
    try:
        await redis_client().set(key, tile, ex=settings.tile_cache_ttl_seconds)
    except RedisError as e:
        logger.warning("Кэш тайлов недоступен на записи: %s", e)


async def close_clients() -> None:
    """Закрыть соединения при остановке приложения."""
    global _http_client, _redis_client

    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
