# Third-party imports
import redis as sync_redis
import redis.asyncio as redis

# Local application imports
from app.settings import settings

connection_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

redis_client: redis.Redis = redis.Redis(connection_pool=connection_pool)

sync_redis_client: sync_redis.Redis = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
