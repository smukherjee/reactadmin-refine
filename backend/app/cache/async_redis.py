"""Async Redis client setup and management."""

from typing import Any, Optional, cast, Callable, Dict
import asyncio

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

try:
    import redis.asyncio as redis_async

    REDIS_ASYNC_AVAILABLE = True
except ImportError:
    redis_async = cast(Any, None)
    REDIS_ASYNC_AVAILABLE = False

logger = get_logger(__name__)

# Global async Redis client
_async_redis_client: Optional[Any] = None


async def get_async_redis_client() -> Optional[Any]:
    """Get the async Redis client instance."""
    return _async_redis_client


async def init_async_redis() -> None:
    """Initialize async Redis connection."""
    global _async_redis_client

    if not REDIS_ASYNC_AVAILABLE:
        logger.warning(
            "redis.asyncio not available, skipping async Redis initialization"
        )
        return

    try:
        # Parse Redis URL from settings
        redis_url = settings.REDIS_URL
        if redis_async is not None:
            _async_redis_client = redis_async.from_url(
                redis_url, encoding="utf-8", decode_responses=True
            )

        # Test connection
        if _async_redis_client:
            await _async_redis_client.ping()
            logger.info("Async Redis client initialized successfully")

    except Exception as e:
        logger.warning(f"Failed to initialize async Redis client: {e}")
        _async_redis_client = None


async def close_async_redis() -> None:
    """Close async Redis connection."""
    global _async_redis_client

    if _async_redis_client:
        try:
            # Use aclose() if available (newer redis versions), fallback to close()
            if hasattr(_async_redis_client, "aclose"):
                await _async_redis_client.aclose()
            else:
                await _async_redis_client.close()
            logger.info("Async Redis client closed successfully")
        except Exception as e:
            logger.error(f"Error closing async Redis client: {e}")
        finally:
            _async_redis_client = None


async def async_redis_available() -> bool:
    """Check if async Redis is available."""
    if not REDIS_ASYNC_AVAILABLE or not _async_redis_client:
        return False

    try:
        await _async_redis_client.ping()
        return True
    except Exception:
        return False


import asyncio
from typing import Callable, Dict


async def async_safe_redis_call(
    fn: Callable[[Any], Any], timeout: float = 0.25
) -> Dict[str, Any]:
    """Run a potentially blocking async Redis operation with an asyncio timeout.

    Returns dict similar to safe_redis_call: {ok, result, elapsed_ms, timeout, error}
    """
    client = _async_redis_client
    if client is None:
        return {
            "ok": False,
            "result": None,
            "elapsed_ms": 0.0,
            "timeout": False,
            "error": "redis client not initialized",
        }

    start = asyncio.get_event_loop().time()
    try:
        coro = fn(client)
        res = await asyncio.wait_for(coro, timeout=timeout)
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
        return {
            "ok": True,
            "result": res,
            "elapsed_ms": round(elapsed_ms, 2),
            "timeout": False,
            "error": None,
        }
    except asyncio.TimeoutError:
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
        return {
            "ok": False,
            "result": None,
            "elapsed_ms": round(elapsed_ms, 2),
            "timeout": True,
            "error": "timeout",
        }
    except Exception as e:
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
        return {
            "ok": False,
            "result": None,
            "elapsed_ms": round(elapsed_ms, 2),
            "timeout": False,
            "error": str(e),
        }
