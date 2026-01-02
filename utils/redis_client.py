import redis
import json
from utils.logger import logger


class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5,
        )

    def ping(self):
        try:
            self.client.ping()
            logger.info("Redis connection successful")
        except Exception as e:
            logger.exception(f"Redis connection failed: {e}")

    # ---------- GET ----------
    def get(self, key: str):
        try:
            value = self.client.get(key)

            if value is not None:
                logger.info(f"Cache hit for key={key}")
                return value

            logger.info(f"Cache miss for key={key}")
            return None

        except Exception as e:
            logger.exception(f"Redis GET failed for key={key}: {e}")
            return None  # safe DB fallback

    # ---------- SET WITH TTL ----------
    def setex(self, key: str, ttl: int, value: str):
        try:
            self.client.setex(key, ttl, value)
            logger.info(f"Cache set for key={key} with ttl={ttl}s")
        except Exception as e:
            logger.exception(f"Redis SETEX failed for key={key}: {e}")

    # ---------- DELETE SINGLE ----------
    def delete(self, key: str):
        try:
            deleted = self.client.delete(key)
            if deleted:
                logger.info(f"Cache invalidated for key={key}")
        except Exception as e:
            logger.exception(f"Redis DELETE failed for key={key}: {e}")

    # ---------- DELETE BY PATTERN ----------
    def delete_pattern(self, pattern: str):
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(
                    f"Cache invalidated for pattern={pattern}, keys_deleted={len(keys)}"
                )
        except Exception as e:
            logger.exception(
                f"Redis DELETE PATTERN failed for pattern={pattern}: {e}"
            )


redis_client = RedisClient()
