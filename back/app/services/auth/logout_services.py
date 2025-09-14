# Standard library imports
import time
from typing import Any

# Third-party imports
from redis.asyncio import RedisError
from redis.asyncio.client import Redis

# Local application imports
from app.core.monitoring.logging import LoggerAdapter

# Redis key prefixes for blocked tokens
BLOCKED_ACCESS_TOKEN_KEY = "blocked_access_token"  # nosec B105
BLOCKED_REFRESH_TOKEN_KEY = "blocked_refresh_token"  # nosec B105


async def logout_user_by_tokens(
    redis_client: Redis,
    logger: LoggerAdapter,
    access_token: str,
    refresh_token: str,
    access_ttl: int,
    refresh_ttl: int,
) -> int | None | Any:
    """
    Logs out the user by blocking their specific access and refresh tokens in Redis for their TTL.

    Args:
        redis_client (redis.client): The Redis client instance.
        logger (LoggerAdapter): The logger adapter instance.
        access_token (str): The access token to block.
        refresh_token (str): The refresh token to block.
        access_ttl (int): Time (in seconds) to block the access token.
        refresh_ttl (int): Time (in seconds) to block the refresh token.

    Raises:
        redis.RedisError: If an error occurs while interacting with Redis.
    """
    try:
        remaining_access_ttl = access_ttl - int(time.time())  # Calculate time remaining

        remaining_refresh_ttl = refresh_ttl - int(time.time())  # Calculate time remaining

        # Block specific access token for its TTL
        await redis_client.setex(
            f"{BLOCKED_ACCESS_TOKEN_KEY}:{access_token}",
            max(remaining_access_ttl, 0),
            "blocked",
        )
        # Block specific refresh token for its TTL
        await redis_client.setex(
            f"{BLOCKED_REFRESH_TOKEN_KEY}:{refresh_token}",
            max(remaining_refresh_ttl, 0),
            "blocked",
        )

    except RedisError as e:
        logger.error(
            f"Error blocking JWT tokens in Redis: {str(e)}",
            extra={"access_token": access_token, "refresh_token": refresh_token},
        )
        raise
    return None


async def is_token_blocked(
    redis_client: Redis,
    token: str,
    is_access_token: bool,
) -> bool:
    """
    Checks if a specific token (access or refresh) is blocked in Redis.

    Args:
        redis_client (redis.client): The Redis client instance.
        token (str): The token to check.
        is_access_token (bool): Whether this is an access token. If False, it's a refresh token.

    Returns:
        bool: True if the token is blocked, False otherwise.
    """
    try:
        token_key_prefix = BLOCKED_ACCESS_TOKEN_KEY if is_access_token else BLOCKED_REFRESH_TOKEN_KEY
        response = await redis_client.exists(f"{token_key_prefix}:{token}")
        return bool(response)

    except RedisError as e:
        raise RuntimeError(f"Error checking token blocked status in Redis: {str(e)}")
