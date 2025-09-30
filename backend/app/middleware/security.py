from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from typing import Optional, Dict, Any
import os
import time
import threading
from starlette.types import ASGIApp

from backend.app.cache import core as cache
from backend.app.cache.async_redis import get_async_redis_client
from backend.app.core.logging import get_logger
from backend.app.core import config

logger = get_logger('middleware.security')


class _InMemoryRateStore:
    """Simple thread-safe in-memory counter store for rate limiting fallback."""

    def __init__(self):
        self._lock = threading.Lock()
        # key -> (count:int, expires_at:float)
        self._store: Dict[str, Any] = {}

    def incr(self, key: str, window: int) -> int:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if entry is None or entry[1] <= now:
                # reset
                self._store[key] = (1, now + window)
                return 1
            count, exp = entry
            count += 1
            self._store[key] = (count, exp)
            return count

    def ttl(self, key: str) -> int:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return -1
            _, exp = entry
            remaining = int(exp - now)
            return remaining if remaining > 0 else -1


_in_memory_store = _InMemoryRateStore()

# Separate in-memory store for sliding-window timestamps to avoid shape conflicts
_in_memory_window_lock = threading.Lock()
_in_memory_window_store: Dict[str, Any] = {}


def clear_in_memory_window_store() -> None:
    """Clear the in-memory sliding-window store. Thread-safe.

    Tests can call this to ensure no state leaks between test cases when
    the rate limiter falls back to the in-memory implementation.
    """
    with _in_memory_window_lock:
        _in_memory_window_store.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-IP rate limiter with Redis fallback.

    Configuration via environment variables:
      RATE_LIMIT_ENABLED (true/false)
      RATE_LIMIT_REQUESTS (int, default 100)
      RATE_LIMIT_WINDOW_SECONDS (int, default 60)
    """

    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:
        super().__init__(app)
        # keep fallbacks; actual values are read at dispatch time to allow test monkeypatching
        self._default_max = int(kwargs.get("max_requests", 100))
        self._default_window = int(kwargs.get("window", 60))

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # read config at dispatch-time to respect runtime env changes (useful for tests)
        # Primary: check environment variable directly (this ensures monkeypatch.setenv works)
        env_val = os.getenv('RATE_LIMIT_ENABLED')
        if env_val is not None:
            if str(env_val).lower() in ('1', 'true', 'yes'):
                enabled = True
            elif str(env_val).lower() in ('0', 'false', 'no'):
                enabled = False
            else:
                enabled = getattr(config.settings, 'RATE_LIMIT_ENABLED', False)
        else:
            # fallback to centralized settings
            enabled = getattr(config.settings, 'RATE_LIMIT_ENABLED', False)
        
        logger.debug(f"RateLimitMiddleware dispatch: resolved enabled={enabled}, env_override={env_val}")

        if not enabled:
            return await call_next(request)

        max_requests = config.settings.RATE_LIMIT_REQUESTS if getattr(config.settings, 'RATE_LIMIT_REQUESTS', None) is not None else self._default_max
        window = config.settings.RATE_LIMIT_WINDOW_SECONDS if getattr(config.settings, 'RATE_LIMIT_WINDOW_SECONDS', None) is not None else self._default_window

        # identify client by remote address; use header override for testing/behind proxies
        client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
        # use route path to scope counters per endpoint
        route = (request.url.path or "/").rstrip("/") or "/"
        key = f"rl:{client_ip}:{route}"

        # Try async Redis first, fallback to in-memory store
        redis_client = await get_async_redis_client()
        
        if redis_client:
            try:
                # Use async Redis sliding window rate limiting
                curr, ttl = await self._async_redis_rate_limit(redis_client, key, max_requests, window)
                backend = "async_redis"
            except Exception as e:
                logger.warning(f"Async Redis rate limiting failed, falling back to in-memory: {e}")
                curr = _in_memory_store.incr(key, window)
                ttl = _in_memory_store.ttl(key)
                backend = "in_memory_fallback"
        else:
            # Use in-memory store when Redis not available
            curr = _in_memory_store.incr(key, window)
            ttl = _in_memory_store.ttl(key)
            backend = "in_memory"

        logger.info(f"Rate limit backend={backend} key={key} curr={curr} ttl={ttl} max={max_requests}")
        if curr > max_requests:
            retry_after = ttl if ttl > 0 else window
            logger.warning("Rate limit exceeded", extra={"client_ip": client_ip, "route": route, "limit": max_requests, "current_count": curr})
            return JSONResponse({"detail": "Rate limit exceeded."}, status_code=429, headers={"Retry-After": str(retry_after)})

        return await call_next(request)
    
    async def _async_redis_rate_limit(self, redis_client: Any, key: str, max_requests: int, window: int) -> tuple[int, int]:
        """Async Redis sliding window rate limiting."""
        now = time.time()
        cutoff = now - window
        
        # Remove old entries and count current requests in sliding window
        pipeline = redis_client.pipeline()
        pipeline.zremrangebyscore(key, 0, cutoff)
        pipeline.zcard(key)
        pipeline.zadd(key, {str(now): now})
        pipeline.expire(key, window)
        
        results = await pipeline.execute()
        current_count = results[1] + 1  # +1 for the request we just added
        
        # Calculate TTL for retry-after header
        oldest_entries = await redis_client.zrange(key, 0, 0, withscores=True)
        if oldest_entries:
            oldest_timestamp = oldest_entries[0][1]
            ttl = int(window - (now - oldest_timestamp))
        else:
            ttl = window
        
        return current_count, ttl



class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add recommended security headers to responses.

    Configurable via environment variables:
      CSP_POLICY: Content Security Policy string (defaults to "default-src 'self'")
      HSTS_MAX_AGE: HSTS max-age in seconds (defaults to 31536000)
    """

    def __init__(self, app):
        super().__init__(app)
        # Use centralized settings
        self.csp = config.settings.CSP_POLICY
        try:
            self.hsts_max_age = int(config.settings.HSTS_MAX_AGE)
        except Exception:
            self.hsts_max_age = 31536000

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # X-Frame-Options
        if "x-frame-options" not in {k.lower() for k in response.headers.keys()}:
            response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        if "x-content-type-options" not in {k.lower() for k in response.headers.keys()}:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy
        if "referrer-policy" not in {k.lower() for k in response.headers.keys()}:
            response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Strict-Transport-Security (HSTS)
        if "strict-transport-security" not in {k.lower() for k in response.headers.keys()}:
            response.headers["Strict-Transport-Security"] = f"max-age={self.hsts_max_age}; includeSubDomains"

        # Content-Security-Policy
        if "content-security-policy" not in {k.lower() for k in response.headers.keys()}:
            response.headers["Content-Security-Policy"] = self.csp

        # X-XSS-Protection (legacy)
        if "x-xss-protection" not in {k.lower() for k in response.headers.keys()}:
            response.headers["X-XSS-Protection"] = "1; mode=block"

        return response
