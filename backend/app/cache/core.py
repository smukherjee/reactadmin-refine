"""Redis cache utilities for caching user permissions and roles.

This file was migrated from the top-level `backend/cache.py` into the `app` package.
Keep the implementation identical to preserve behavior; callers can be updated to import
from `app.cache.core` incrementally.
"""

import concurrent.futures
import json
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union, cast

import redis
import redis.asyncio as redis_async

from backend.app.core.logging import get_logger, log_cache_operation
from backend.app.core.config import settings

logger = get_logger("cache")

# Redis configuration

REDIS_URL = settings.REDIS_URL
CACHE_TTL = settings.CACHE_TTL
INVALIDATION_CHANNEL = "app:cache-invalidate"

# Redis client instance (use Any at runtime but cast to Redis where needed)
redis_client: Optional[Any] = None
# Async async-redis client (created during app startup)
async_redis_client: Optional[redis_async.Redis] = None
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


def safe_redis_call(fn: Callable[[Any], Any], timeout: float = 0.25) -> Dict[str, Any]:
    """Run a potentially blocking Redis operation in a thread with a timeout.

    Args:
        fn: Callable that accepts a redis client and performs an operation (e.g. lambda c: c.ping()).
        timeout: timeout in seconds for the operation.

    Returns a dict with keys:
        ok: bool - whether call completed successfully
        result: the return value from fn on success, else None
        elapsed_ms: float - elapsed time in ms for the attempted call (0.0 if not attempted)
        timeout: bool - whether the call timed out
        error: Optional[str] - exception string if any
    """
    client = get_redis_client()
    if client is None:
        return {
            "ok": False,
            "result": None,
            "elapsed_ms": 0.0,
            "timeout": False,
            "error": "redis client not initialized",
        }

    start = time.time()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(fn, client)
            try:
                res = fut.result(timeout=timeout)
                elapsed_ms = (time.time() - start) * 1000
                return {
                    "ok": True,
                    "result": res,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "timeout": False,
                    "error": None,
                }
            except concurrent.futures.TimeoutError:
                elapsed_ms = (time.time() - start) * 1000
                return {
                    "ok": False,
                    "result": None,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "timeout": True,
                    "error": "timeout",
                }
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return {
            "ok": False,
            "result": None,
            "elapsed_ms": round(elapsed_ms, 2),
            "timeout": False,
            "error": str(e),
        }


def get_async_redis_client() -> Optional[redis_async.Redis]:
    """Return the module-level async redis client if available."""
    return async_redis_client


def is_redis_available() -> bool:
    """Check if Redis is available without pinging every time."""
    return get_redis_client() is not None


def cache_key(
    prefix: str,
    *args: Any,
    tenant_id: Union[str, uuid.UUID, None] = None,
) -> str:
    """Generate a cache key optionally namespaced by tenant_id then prefix and arguments.

    Example: cache_key('user_permissions', user_id, tenant_id=tenant_id) -> "<tenant_id>:user_permissions:<user_id>"
    """
    parts = []
    if tenant_id is not None:
        parts.append(str(tenant_id))
    parts.append(prefix)
    for arg in args:
        parts.append(str(arg))
    return ":".join(parts)


def get_cached(key: str) -> Optional[Any]:
    """Get value from cache."""
    start_time = time.time()

    client = get_redis_client()
    if client is None:
        log_cache_operation("get", key, hit=False)
        return None

    # Use safe helper to bound get operation
    resp = safe_redis_call(lambda c: c.get(key), timeout=0.25)
    duration_ms = resp.get("elapsed_ms", 0.0)
    if resp.get("ok") and resp.get("result") is not None:
        try:
            raw = resp.get("result")
            if raw is None:
                return None
            result = json.loads(raw)
            log_cache_operation("get", key, hit=True, duration_ms=duration_ms)
            return result
        except Exception:
            log_cache_operation("get", key, hit=True, duration_ms=duration_ms)
            return resp.get("result")
    else:
        log_cache_operation("get", key, hit=False, duration_ms=duration_ms)
        if resp.get("error"):
            logger.debug(f"Cache get error for key {key}: {resp.get('error')}")
        return None


def set_cached(key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
    """Set value in cache with TTL."""
    start_time = time.time()

    client = get_redis_client()
    if client is None:
        log_cache_operation("set", key)
        return False

    try:
        serialized = json.dumps(value, default=str)
        resp = safe_redis_call(lambda c: c.setex(key, ttl, serialized), timeout=0.25)
        duration_ms = resp.get("elapsed_ms", 0.0)
        log_cache_operation("set", key, duration_ms=duration_ms)
        return resp.get("ok", False)
    except Exception as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        return False


def delete_cached(key: str) -> bool:
    """Delete key from cache."""
    client = get_redis_client()
    if client is None:
        return False
    resp = safe_redis_call(lambda c: c.delete(key), timeout=0.25)
    if not resp.get("ok") and resp.get("error"):
        logger.debug(f"Cache delete error for key {key}: {resp.get('error')}")
    return resp.get("ok", False)


def delete_pattern(pattern: str) -> int:
    """Delete all keys matching pattern."""
    client = get_redis_client()
    if client is None:
        return 0

    keys_resp = safe_redis_call(lambda c: c.keys(pattern), timeout=0.5)
    if not keys_resp.get("ok"):
        logger.debug(
            f"Cache pattern keys error for pattern {pattern}: {keys_resp.get('error')}"
        )
        return 0

    keys = keys_resp.get("result") or []
    if not keys:
        return 0

    del_resp = safe_redis_call(lambda c: c.delete(*keys), timeout=0.5)
    if del_resp.get("ok"):
        return del_resp.get("result") or 0
    else:
        logger.debug(
            f"Cache pattern delete error for pattern {pattern}: {del_resp.get('error')}"
        )
        return 0


# (No legacy helpers) All cache functions require explicit tenant_id + id parameters.
def invalidate_user_cache(
    tenant_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID]
) -> dict:
    """Invalidate all cache entries for a user within a tenant.

    This function requires both client_id and user_id to be provided. Keys are tenant-prefixed.
    """
    user_id_str = str(user_id)
    tid = str(tenant_id)
    keys = [
        cache_key("user_permissions", user_id_str, tenant_id=tid),
        cache_key("user_roles", user_id_str, tenant_id=tid),
        cache_key("user_data", user_id_str, tenant_id=tid),
    ]
    for k in keys:
        delete_cached(k)
    publish_invalidation(
        {
            "type": "user_permissions_invalidate",
            "user_id": user_id_str,
            "tenant_id": tid,
        }
    )


def invalidate_role_cache(
    tenant_id: Union[str, uuid.UUID], role_id: Union[str, uuid.UUID]
) -> None:
    """Invalidate cache entries related to a role within a tenant."""
    role_id_str = str(role_id)
    tid = str(tenant_id)
    delete_pattern(f"{tid}:user_permissions:*")
    delete_pattern(f"{tid}:user_roles:*")
    publish_invalidation(
        {"type": "role_invalidate", "role_id": role_id_str, "tenant_id": tid}
    )


def cache_user_permissions(
    tenant_id: Union[str, uuid.UUID],
    user_id: Union[str, uuid.UUID],
    permissions: List[str],
) -> None:
    """Cache user permissions for a tenant (requires tenant_id and user_id)."""
    key = cache_key("user_permissions", user_id, tenant_id=tenant_id)
    set_cached(key, permissions)


def get_cached_user_permissions(
    tenant_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID]
) -> Optional[List[str]]:
    """Get cached user permissions for a tenant (requires tenant_id and user_id)."""
    key = cache_key("user_permissions", user_id, tenant_id=tenant_id)
    return get_cached(key)


def cache_user_roles(
    tenant_id: Union[str, uuid.UUID],
    user_id: Union[str, uuid.UUID],
    roles: List[Dict[str, Any]],
) -> None:
    """Cache user roles for a tenant."""
    key = cache_key("user_roles", user_id, tenant_id=tenant_id)
    set_cached(key, roles)


def get_cached_user_roles(
    tenant_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID]
) -> Optional[List[Dict[str, Any]]]:
    """Get cached user roles for a tenant."""
    key = cache_key("user_roles", user_id, tenant_id=tenant_id)
    return get_cached(key)


def clear_all_cache() -> None:
    """Clear all cache entries (for testing)."""
    client = get_redis_client()
    if client is None:
        return
    resp = safe_redis_call(lambda c: c.flushdb(), timeout=1.0)
    if not resp.get("ok") and resp.get("error"):
        logger.debug(f"Cache clear error: {resp.get('error')}")


def publish_invalidation(message: Dict[str, Any]) -> bool:
    """Publish a cache invalidation message to other processes."""
    client = get_redis_client()
    if client is None:
        return False
    resp = safe_redis_call(
        lambda c: c.publish(INVALIDATION_CHANNEL, json.dumps(message)), timeout=0.25
    )
    if not resp.get("ok") and resp.get("error"):
        logger.debug(f"Failed to publish invalidation: {resp.get('error')}")
    return resp.get("ok", False)


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
