"""Redis cache utilities for caching user permissions and roles.

This file was migrated from the top-level `backend/cache.py` into the `app` package.
Keep the implementation identical to preserve behavior; callers can be updated to import
from `app.cache.core` incrementally.
"""

import json
import os
from typing import Optional, List, Any, Dict, Union, Callable, cast
import redis
from redis import Redis
import uuid
import logging

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default
INVALIDATION_CHANNEL = "app:cache-invalidate"

# Redis client instance (use Any at runtime but cast to Redis where needed)
redis_client: Optional[Any] = None
_pubsub_thread_started = False


def get_redis_client() -> Optional[Any]:
    """Get Redis client instance, creating it if needed. Returns None if not available."""
    global redis_client
    if redis_client is not None:
        return redis_client
    try:
        rc = redis.from_url(REDIS_URL, decode_responses=True)
        # ping once to validate the connection
        rc.ping()
        redis_client = rc
        logger.info("Redis connection established")
        return redis_client
    except Exception as e:
        logger.debug(f"Redis connection unavailable: {e}")
        redis_client = None
        return None


def is_redis_available() -> bool:
    """Check if Redis is available without pinging every time."""
    return get_redis_client() is not None


def cache_key(prefix: str, *args: Union[str, uuid.UUID], client_id: Union[str, uuid.UUID, None] = None) -> str:
    """Generate a cache key optionally namespaced by client_id then prefix and arguments.

    Example: cache_key('user_permissions', user_id, client_id=client_id) -> "<client_id>:user_permissions:<user_id>"
    """
    parts = []
    if client_id is not None:
        parts.append(str(client_id))
    parts.append(prefix)
    for arg in args:
        parts.append(str(arg))
    return ":".join(parts)


def get_cached(key: str) -> Optional[Any]:
    """Get value from cache."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        value = cast(Any, client).get(key)
        if value is not None:
            # ensure we have a string for json.loads (redis is configured with decode_responses=True)
            return json.loads(value)
    except Exception as e:
        logger.warning(f"Cache get error for key {key}: {e}")
    return None


def set_cached(key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
    """Set value in cache with TTL."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        serialized = json.dumps(value, default=str)
        cast(Any, client).setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False


def delete_cached(key: str) -> bool:
    """Delete key from cache."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        cast(Any, client).delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        return False


def delete_pattern(pattern: str) -> int:
    """Delete all keys matching pattern."""
    client = get_redis_client()
    if client is None:
        return 0
    try:
        keys = cast(Any, client).keys(pattern)
        if keys:
            # keys may be an iterable of bytes/str; pass through to delete
            return cast(Any, client).delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache pattern delete error for pattern {pattern}: {e}")
        return 0


# (No legacy helpers) All cache functions require explicit client_id + id parameters.
def invalidate_user_cache(client_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID]) -> None:
    """Invalidate all cache entries for a user within a tenant.

    This function requires both client_id and user_id to be provided. Keys are tenant-prefixed.
    """
    user_id_str = str(user_id)
    cid = str(client_id)
    keys = [
        cache_key("user_permissions", user_id_str, client_id=cid),
        cache_key("user_roles", user_id_str, client_id=cid),
        cache_key("user_data", user_id_str, client_id=cid),
    ]
    for k in keys:
        delete_cached(k)
    publish_invalidation({"type": "user_permissions_invalidate", "user_id": user_id_str, "client_id": cid})


def invalidate_role_cache(client_id: Union[str, uuid.UUID], role_id: Union[str, uuid.UUID]) -> None:
    """Invalidate cache entries related to a role within a tenant."""
    role_id_str = str(role_id)
    cid = str(client_id)
    delete_pattern(f"{cid}:user_permissions:*")
    delete_pattern(f"{cid}:user_roles:*")
    publish_invalidation({"type": "role_invalidate", "role_id": role_id_str, "client_id": cid})


def cache_user_permissions(client_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID], permissions: List[str]) -> None:
    """Cache user permissions for a tenant (requires client_id and user_id)."""
    key = cache_key("user_permissions", user_id, client_id=client_id)
    set_cached(key, permissions)


def get_cached_user_permissions(client_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID]) -> Optional[List[str]]:
    """Get cached user permissions for a tenant (requires client_id and user_id)."""
    key = cache_key("user_permissions", user_id, client_id=client_id)
    return get_cached(key)


def cache_user_roles(client_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID], roles: List[Dict[str, Any]]) -> None:
    """Cache user roles for a tenant."""
    key = cache_key("user_roles", user_id, client_id=client_id)
    set_cached(key, roles)


def get_cached_user_roles(client_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID]) -> Optional[List[Dict[str, Any]]]:
    """Get cached user roles for a tenant."""
    key = cache_key("user_roles", user_id, client_id=client_id)
    return get_cached(key)


def clear_all_cache() -> None:
    """Clear all cache entries (for testing)."""
    client = get_redis_client()
    if client is None:
        return
    try:
        cast(Any, client).flushdb()
    except Exception as e:
        logger.warning(f"Cache clear error: {e}")


def publish_invalidation(message: Dict[str, Any]) -> bool:
    """Publish a cache invalidation message to other processes."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        cast(Any, client).publish(INVALIDATION_CHANNEL, json.dumps(message))
        return True
    except Exception as e:
        logger.warning(f"Failed to publish invalidation: {e}")
        return False


def start_invalidation_listener(handler: Callable[[Dict[str, Any]], None]) -> None:
    """Start a background thread that listens for invalidation messages and calls handler(payload).

    handler should be a callable that accepts a dict.
    """
    global _pubsub_thread_started
    if _pubsub_thread_started:
        return
    client = get_redis_client()
    if client is None:
        return
    pubsub = cast(Any, client).pubsub(ignore_subscribe_messages=True)
    try:
        pubsub.subscribe(INVALIDATION_CHANNEL)
    except Exception as e:
        logger.warning(f"Failed to subscribe to invalidation channel: {e}")
        return

    import threading

    def run():
        for item in pubsub.listen():
            if item and item.get("type") == "message":
                try:
                    payload = json.loads(item["data"])
                    handler(payload)
                except Exception:
                    logger.exception("Invalid invalidation payload")

    t = threading.Thread(target=run, daemon=True)
    t.start()
    _pubsub_thread_started = True
