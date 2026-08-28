"""
Подключение к Redis.

Отдельным модулем, а не внутри сервиса тайлов: клиент нужен ещё счётчику
показателей и ограничителю частоты, а тащить их всех через сервис тайлов —
это цикл импортов и странная зависимость. Рядом с database.py: там Postgres,
здесь Redis.
"""

from redis.asyncio import Redis

from app.config import settings

_client: Redis | None = None


def redis_client() -> Redis:
    """Общий на процесс клиент. Соединения он держит сам, пулом внутри."""
    global _client

    if _client is None:
        _client = Redis.from_url(settings.redis_url)
    return _client


async def close_redis() -> None:
    """Закрыть соединение при остановке приложения."""
    global _client

    if _client is not None:
        await _client.aclose()
        _client = None
