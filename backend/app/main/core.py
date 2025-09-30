import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type, Union, cast

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from jose import jwt
from sqlalchemy.orm import Session

# auth and crud core modules
from backend.app.auth import core as auth
from backend.app.cache import core as cache
from backend.app.crud import core as crud
from backend.app.crud.core import (
    create_session,
    get_session_by_refresh_hash,
    get_sessions_by_user,
    revoke_all_sessions,
    revoke_session,
    rotate_refresh_token,
)
from backend.app.db.core import Base, get_db, get_engine
from backend.app.models import core as models
from backend.app.schemas import core as schemas

load_dotenv()

from backend.app.core.config import settings
from backend.app.core.init import init_app

# Configure structured logging
from backend.app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

from backend.app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
# Tenant cookie configuration
TENANT_COOKIE_NAME = settings.TENANT_COOKIE_NAME
TENANT_COOKIE_SECURE = settings.TENANT_COOKIE_SECURE


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: initialize cache and pub/sub listener."""
    # Centralized initialization: initialize DB engine and synchronous cache
    # client first so subsequent async initializers can assume resources exist.
    try:
        init_app()
    except Exception:
        pass

    # start invalidation listener to handle messages from other processes
    def _invalidation_handler(payload: dict):
        try:
            t = payload.get("type")
            if t == "user_permissions_invalidate":
                uid = payload.get("user_id")
                cid = payload.get("client_id")
                if uid and cid:
                    cache.invalidate_user_cache(cid, uid)
            elif t == "role_invalidate":
                rid = payload.get("role_id")
                cid = payload.get("client_id")
                if rid and cid:
                    cache.invalidate_role_cache(cid, rid)
        except Exception:
            logger.exception("Error handling invalidation payload")

    # Check Redis availability using safe helper to avoid blocking startup
    try:
        ping_resp = cache.safe_redis_call(lambda c: c.ping(), timeout=0.25)
        if ping_resp.get("ok"):
            logger.info("Redis cache initialized successfully")
            cache.start_invalidation_listener(_invalidation_handler)
        else:
            logger.warning(
                "Redis cache not available - running without cache (ping failed or timed out)"
            )
    except Exception:
        logger.warning("Redis cache not available - running without cache")

    # Create async redis client for async codepaths (using aioredis)
    try:
        from backend.app.cache.async_redis import init_async_redis

        await init_async_redis()
    except Exception as e:
        logger.debug(f"Failed to initialize aioredis client: {e}")

    # Start background system metrics collection
    try:
        from backend.app.services.system_metrics import (
            start_background_metrics_collection,
        )

        await start_background_metrics_collection()
    except Exception as e:
        logger.warning(f"Failed to start system metrics collection: {e}")

    # Legacy async redis client (using redis.asyncio) - keep for compatibility
    try:
        import redis.asyncio as redis_async

        from backend.app.cache import core as cache_core

        if cache_core.async_redis_client is None and cache_core.REDIS_URL:
            try:
                cache_core.async_redis_client = redis_async.from_url(
                    cache_core.REDIS_URL, encoding="utf-8", decode_responses=True
                )
                logger.info("Legacy async Redis client initialized")
            except Exception:
                logger.debug(
                    "Failed to initialize legacy async redis client; continuing without it"
                )
    except Exception:
        logger.debug("redis.asyncio not available or failed to import")

    yield

    # shutdown
    if cache.redis_client:
        try:
            cache.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
    # Stop background system metrics collection
    try:
        from backend.app.services.system_metrics import (
            stop_background_metrics_collection,
        )

        await stop_background_metrics_collection()
    except Exception as e:
        logger.warning(f"Error stopping system metrics collection: {e}")

    # Close aioredis client
    try:
        from backend.app.cache.async_redis import close_async_redis

        await close_async_redis()
    except Exception as e:
        logger.warning(f"Error closing aioredis client: {e}")

    # close legacy async redis client if present
    try:
        from backend.app.cache import core as cache_core

        async_client = getattr(cache_core, "async_redis_client", None)
        if async_client is not None:
            try:
                # prefer aclose() if available (redis.asyncio.Redis implements aclose)
                if hasattr(async_client, "aclose"):
                    await async_client.aclose()
                elif hasattr(async_client, "close"):
                    # close may be coroutine in some versions
                    maybe_coro = async_client.close()
                    if hasattr(maybe_coro, "__await__"):
                        await maybe_coro
                logger.info("Async Redis client closed")
            except Exception:
                logger.debug("Failed to close async redis client cleanly")
    except Exception:
        pass


app = FastAPI(
    title="ReactAdmin-Refine Backend",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

from starlette.middleware.base import BaseHTTPMiddleware

# Attach middleware for tenant extraction and RBAC payload
# Attach middleware for tenant extraction and RBAC payload
from backend.app.middleware.core import TenantRBACMiddleware
from backend.app.middleware.logging import (
    PerformanceLoggingMiddleware,
    RequestLoggingMiddleware,
)
from backend.app.middleware.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)

# Add logging middleware (order matters - add these first)
app.add_middleware(PerformanceLoggingMiddleware, slow_request_threshold=1000.0)
app.add_middleware(
    RequestLoggingMiddleware,
    log_request_body=settings.LOG_REQUEST_BODY,
    log_response_body=settings.LOG_RESPONSE_BODY,
)
# Security and rate limiting: add after logging middleware so events are captured
# Always register the RateLimitMiddleware so tests can toggle it at runtime via
# centralized settings and reload_settings(); the middleware itself consults
# settings.RATE_LIMIT_ENABLED at dispatch time and will be a no-op when disabled.
app.add_middleware(cast(Type[BaseHTTPMiddleware], RateLimitMiddleware))
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantRBACMiddleware)

# Add lightweight GZip compression for larger responses
app.add_middleware(GZipMiddleware, minimum_size=500)

from backend.app.api.v1 import router as v1_router

# Include v2 async API router (exposed under both /api/v2 and /api/v1 for
# backward compatibility during migration). The legacy v1 package has been
# removed; v2 contains equivalent sync/async implementations. Exposing v2
# under /api/v1 avoids breaking clients while we remove the old code.
from backend.app.api.v2 import router as v2_router

# Include async v2 router at canonical path
app.include_router(v2_router, prefix="/api/v2")

# For /api/v1 we want the legacy sync router to take precedence. Include
# the v1 sync router first, then mount v2 under the same prefix so any
# missing routes still resolve to async implementations.
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v1")

# During migration we previously exposed v1 at the root for compatibility.
# That shim has been removed: v1 endpoints are available under /api/v1 only.

# create tables if not exist (helpful for initial run)
# Initialize the sync engine and then create tables. This avoids creating
# engines at module import time and supports tests/CI that set DATABASE_URL
# before initialization.
try:
    _engine = get_engine()
    if _engine is not None:
        Base.metadata.create_all(bind=_engine)
except Exception:
    # If initialization fails (for example missing drivers), continue; app
    # startup or tests will initialize the engine when needed.
    pass


# Note: legacy root routes have been moved into `/api/v1` (sync) and `/api/v2` (async)
# The original route implementations were migrated into router modules under backend.app.api.v1 and backend.app.api.v2


@app.get("/health/detailed")
def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check endpoint using shared health service."""
    from backend.app.services.health import collect_detailed_health

    overall_status, components, timings = collect_detailed_health(db)

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "components": components,
    }


# The v1 sync router (included above) exposes legacy /api/v1/* endpoints.
# We avoid duplicating those handlers here so routing is sourced from the
# sync implementation under `backend.app.api.v1`.


@app.get("/readiness")
def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.
    Checks if the application is ready to receive traffic.
    """
    try:
        from sqlalchemy import text

        # Test critical dependencies
        db.execute(text("SELECT 1"))

        # Use centralized safe_redis_call to avoid blocking on redis
        try:
            ping_resp = cache.safe_redis_call(lambda c: c.ping(), timeout=0.25)
            if not ping_resp.get("ok") and ping_resp.get("error"):
                raise Exception(f"redis ping failed: {ping_resp.get('error')}")
        except Exception as e:
            # treat redis ping failure as readiness failure
            raise

        return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@app.get("/liveness")
def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Checks if the application is alive and should not be restarted.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
