import redis
from app.core.config import settings

# Create Redis connection
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    decode_responses=True
)


def get_redis():
    """Dependency to get Redis client"""
    return redis_client
