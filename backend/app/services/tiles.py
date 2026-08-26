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

import hashlib
import logging

import httpx
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings
from app.exceptions import NotFoundError, UpstreamError
from app.models.round import Round
from app.services.game import max_local_zoom

logger = logging.getLogger(__name__)

TILE_CONTENT_TYPE = "image/jpeg"

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


def _get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url)
    return _redis_client


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

    cached = await _cache_get(cache_key)
    if cached is not None:
        return cached

    url = settings.satellite_tile_url.format(z=source_z, x=source_x, y=source_y)

    try:
        response = await _get_http_client().get(url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Провайдер снимков не отдал тайл %s: %s", url, e)
        raise UpstreamError("Провайдер снимков недоступен") from e

    tile = response.content
    await _cache_set(cache_key, tile)
    return tile


async def _cache_get(key: str) -> bytes | None:
    """Достать тайл из кэша. Недоступный Redis не должен ронять игру."""
    try:
        return await _get_redis_client().get(key)
    except RedisError as e:
        logger.warning("Кэш тайлов недоступен на чтении: %s", e)
        return None


async def _cache_set(key: str, tile: bytes) -> None:
    """Положить тайл в кэш. Недоступный Redis не должен ронять игру."""
    try:
        await _get_redis_client().set(key, tile, ex=settings.tile_cache_ttl_seconds)
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
