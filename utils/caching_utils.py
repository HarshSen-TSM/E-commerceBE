import json
from typing import Callable, Any, Optional

from utils.redis_client import redis_client
from utils.logger import logger


def get_or_set_cache(
    *,
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Any],
) -> Optional[Any]:
    """
    Generic cache helper using Cache-Aside pattern.

    Flow:
    1. Try Redis (read-through)
    2. On cache miss, fetch from source (DB/service)
    3. Store result in Redis with TTL
    4. Return data

    Notes:
    - Redis failures never break API execution
    - Cache logging is handled inside RedisClient
    """

    # ---------- CACHE READ ----------
    cached = redis_client.get(key)
    if cached is not None:
        try:
            return json.loads(cached)
        except Exception as e:
            logger.exception(f"Failed to deserialize cache value for key={key}: {e}")

    # ---------- CACHE MISS → FETCH ----------
    data = fetch_fn()

    # ---------- CACHE WRITE ----------
    try:
        redis_client.setex(key, ttl, json.dumps(data))
    except Exception as e:
        logger.exception(f"Failed to cache data for key={key}: {e}")

    return data
