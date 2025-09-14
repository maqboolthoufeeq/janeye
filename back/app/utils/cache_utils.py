# Standard library imports
import json
from typing import Any

# Local application imports
from app.core.caching.redis import redis_client
from app.core.monitoring.logging import get_contextual_logger

logger = get_contextual_logger(__name__)


async def get_cached_data(cache_key: str) -> Any | None:
    """Get data from Redis cache if it exists"""
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        return None
    except Exception as e:
        logger.error(f"Error retrieving from cache: {str(e)}")
        return None


async def set_cached_data(cache_key: str, data: Any, expiry_seconds: int) -> None:
    """Set data in Redis cache with expiration time"""
    try:
        await redis_client.set(cache_key, json.dumps(data, default=str), ex=expiry_seconds)
        logger.debug(f"Cached data with key: {cache_key} for {expiry_seconds} seconds")
    except Exception as e:
        logger.error(f"Error setting cache: {str(e)}")


async def invalidate_cache_pattern(pattern: str) -> None:
    """Invalidate all cache keys matching a pattern"""
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {str(e)}")


async def delete_cached_data(cache_key: str) -> None:
    """Delete specific cache key"""
    try:
        await redis_client.delete(cache_key)
        logger.debug(f"Deleted cache key: {cache_key}")
    except Exception as e:
        logger.error(f"Error deleting cache key {cache_key}: {str(e)}")
