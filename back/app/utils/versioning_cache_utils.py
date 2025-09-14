# Standard library imports
from typing import Any

# Local application imports
from app.core.caching.redis import sync_redis_client
from app.core.monitoring.logging import get_contextual_logger

logger = get_contextual_logger(__name__)


def get_versioning_cache_key(platform_type: Any) -> str:
    """
    Generate a cache key for a specific platform.

    Args:
        platform_type: The platform type can be either the enum or its string value

    Returns:
        A consistent cache key string
    """
    # Ensure we always use the string value for consistent keys
    if hasattr(platform_type, "value"):
        platform_value = platform_type.value
    else:
        platform_value = str(platform_type)

    return f"VERSIONING:{platform_value}"


def invalidate_versioning_cache(target: Any) -> None:
    """Invalidate cache for a versioning object."""
    try:
        platform = target.platform
        cache_key = get_versioning_cache_key(platform)

        sync_redis_client.delete(cache_key)
        logger.info(f"Invalidated cache for {platform}, key: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")
        # Don't let cache invalidation failure break the database operation
