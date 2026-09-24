"""Public surface of the redis package.

Call sites import from here — `from app.core.redis import get_redis` — and never
care whether that's one file or several. As Redis usage grows (rate limiting in
Phase 2, Streams in Phase 3, pub/sub later), add sibling modules here
(rate_limit.py, streams.py, ...) and re-export their public functions below,
rather than growing client.py into a grab-bag.
"""

from app.core.redis.client import check_redis_connection, get_redis

__all__ = ["check_redis_connection", "get_redis"]
