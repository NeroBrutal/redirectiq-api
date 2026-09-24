"""Async Redis client, created lazily and shared for the life of the process.

Absolute imports (the Python 3 default) mean `from redis.asyncio import Redis`
below resolves to the third-party `redis` package, not this local `app.core.redis`
package, even though they share a name — Python only reaches this package via the
dotted path `app.core.redis`. No alias/rename needed.
"""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def check_redis_connection() -> bool:
    """Used by /health. Returns False instead of raising."""
    try:
        return await get_redis().ping()
    except Exception:
        return False
