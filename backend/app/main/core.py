from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.orm import Session
from backend.app.cache import core as cache
# auth and crud core modules
from backend.app.auth import core as auth
from backend.app.crud import core as crud
from backend.app.models import core as models
from backend.app.schemas import core as schemas
from backend.app.db.core import engine, Base, get_db
import os
from dotenv import load_dotenv
from datetime import timedelta, datetime, timezone
from jose import jwt
import secrets
from backend.app.crud.core import create_session, get_session_by_refresh_hash, rotate_refresh_token, revoke_session
from backend.app.crud.core import get_sessions_by_user, revoke_all_sessions
from typing import Any, Dict, List, Optional, Type, Union, cast
import uuid
import logging

load_dotenv()

# Configure structured logging
from backend.app.core.logging import setup_logging, get_logger
from backend.app.core.config import settings

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
    client = cache.get_redis_client()
    if client:
        logger.info("Redis cache initialized successfully")
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

        cache.start_invalidation_listener(_invalidation_handler)
    else:
        logger.warning("Redis cache not available - running without cache")

    # Create async redis client for async codepaths (using aioredis)
    try:
        from backend.app.cache.async_redis import init_async_redis
        await init_async_redis()
    except Exception as e:
        logger.debug(f"Failed to initialize aioredis client: {e}")
    
    # Start background system metrics collection
    try:
        from backend.app.services.system_metrics import start_background_metrics_collection
        await start_background_metrics_collection()
    except Exception as e:
        logger.warning(f"Failed to start system metrics collection: {e}")
    
    # Legacy async redis client (using redis.asyncio) - keep for compatibility
    try:
        from backend.app.cache import core as cache_core
        import redis.asyncio as redis_async
        if cache_core.async_redis_client is None and cache_core.REDIS_URL:
            try:
                cache_core.async_redis_client = redis_async.from_url(cache_core.REDIS_URL, encoding="utf-8", decode_responses=True)
                logger.info("Legacy async Redis client initialized")
            except Exception:
                logger.debug("Failed to initialize legacy async redis client; continuing without it")
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
        from backend.app.services.system_metrics import stop_background_metrics_collection
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
        async_client = getattr(cache_core, 'async_redis_client', None)
        if async_client is not None:
            try:
                # prefer aclose() if available (redis.asyncio.Redis implements aclose)
                if hasattr(async_client, 'aclose'):
                    await async_client.aclose()
                elif hasattr(async_client, 'close'):
                    # close may be coroutine in some versions
                    maybe_coro = async_client.close()
                    if hasattr(maybe_coro, '__await__'):
                        await maybe_coro
                logger.info("Async Redis client closed")
            except Exception:
                logger.debug("Failed to close async redis client cleanly")
    except Exception:
        pass


app = FastAPI(title="ReactAdmin-Refine Backend", lifespan=lifespan, default_response_class=ORJSONResponse)

# Attach middleware for tenant extraction and RBAC payload
# Attach middleware for tenant extraction and RBAC payload
from backend.app.middleware.core import TenantRBACMiddleware
from backend.app.middleware.logging import RequestLoggingMiddleware, PerformanceLoggingMiddleware
from backend.app.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Add logging middleware (order matters - add these first)
app.add_middleware(PerformanceLoggingMiddleware, slow_request_threshold=1000.0)
app.add_middleware(RequestLoggingMiddleware,
                  log_request_body=settings.LOG_REQUEST_BODY,
                  log_response_body=settings.LOG_RESPONSE_BODY)
# Security and rate limiting: add after logging middleware so events are captured
# Always register the RateLimitMiddleware so tests can toggle it at runtime via
# centralized settings and reload_settings(); the middleware itself consults
# settings.RATE_LIMIT_ENABLED at dispatch time and will be a no-op when disabled.
app.add_middleware(cast(Type[BaseHTTPMiddleware], RateLimitMiddleware))
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantRBACMiddleware)

# Add lightweight GZip compression for larger responses
app.add_middleware(GZipMiddleware, minimum_size=500)

# Include v1 API router for versioning
from backend.app.api.v1 import router as v1_router
app.include_router(v1_router, prefix="/api/v1")

# Include v2 async API router
from backend.app.api.v2 import router as v2_router
app.include_router(v2_router, prefix="/api/v2")

# For backward compatibility during the migration we previously exposed v1 at
# the root. That compatibility shim has been removed so v1 endpoints are only
# available under the /api/v1 prefix.
# NOTE: Re-introduce a lightweight compatibility shim while tests are migrated.
# This should be removed once tests and clients fully use the /api/v1 and /api/v2 prefixes.
app.include_router(v1_router)

# create tables if not exist (helpful for initial run)
Base.metadata.create_all(bind=engine)


# Note: legacy root routes have been moved into `/api/v1` (sync) and `/api/v2` (async)
# The original route implementations were migrated into router modules under backend.app.api.v1 and backend.app.api.v2


@app.get("/health/detailed")
def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check endpoint.
    Checks all critical components: database, redis, system resources.
    """
    import time
    import psutil
    
    components = {}
    overall_status = "healthy"
    
    # Check database health
    try:
        from sqlalchemy import text
        db_start = time.time()
        db.execute(text("SELECT 1"))
        db_response_time = (time.time() - db_start) * 1000
        
        components["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2)
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "degraded"
    
    # Check Redis health
    try:
        redis_client = cache.get_redis_client()
        if redis_client:
            redis_start = time.time()
            redis_client.ping()
            redis_response_time = (time.time() - redis_start) * 1000
            
            # Get Redis info
            redis_info = redis_client.info()
            
            components["redis"] = {
                "status": "healthy",
                "response_time_ms": round(redis_response_time, 2),
                "memory_usage_mb": round(redis_info.get("used_memory", 0) / 1024 / 1024, 2),
                "connected_clients": redis_info.get("connected_clients", 0)
            }
        else:
            components["redis"] = {
                "status": "unavailable",
                "error": "Redis client not initialized"
            }
            overall_status = "degraded"
    except Exception as e:
        components["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "degraded"
    
    # Check system resources (using cached metrics to avoid blocking)
    try:
        from backend.app.services.system_metrics import get_cached_system_metrics
        system_metrics = get_cached_system_metrics()
        components["system"] = system_metrics
        
        if system_metrics.get("status") != "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["system"] = {
            "status": "unhealthy", 
            "error": str(e)
        }
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    "version": settings.APP_VERSION,
    "environment": settings.ENVIRONMENT,
        "components": components
    }


@app.get("/metrics")
def system_metrics():
    """
    System metrics endpoint for monitoring.
    Returns key system performance indicators.
    """
    import time
    
    try:
        from backend.app.services.system_metrics import get_cached_system_metrics
        system_metrics = get_cached_system_metrics()
        
        # Extract key metrics for the metrics endpoint
        metrics = {
            "cpu_percent": system_metrics.get("cpu_percent", 0),
            "memory_percent": system_metrics.get("memory_percent", 0),
            "memory_available_mb": system_metrics.get("memory_available_mb", 0),
            "disk_usage_percent": system_metrics.get("disk_usage_percent", 0),
        }
        
        # Calculate uptime from process metrics if available
        process_info = system_metrics.get("process", {})
        if process_info:
            metrics["process_memory_mb"] = process_info.get("memory_mb", 0)
            metrics["process_cpu_percent"] = process_info.get("cpu_percent", 0)
        
        # Add approximate uptime (fallback calculation)
        import psutil
        try:
            process = psutil.Process(os.getpid()) 
            uptime_seconds = time.time() - process.create_time()
            metrics["uptime_seconds"] = round(uptime_seconds, 2)
        except Exception:
            metrics["uptime_seconds"] = 0
        
        return metrics
        
    except Exception as e:
        # Fallback to direct psutil calls if system metrics service fails
        import psutil
        process = psutil.Process(os.getpid())
        uptime_seconds = time.time() - process.create_time()
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2),
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "uptime_seconds": round(uptime_seconds, 2),
            "metrics_service_error": str(e)
        }


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
        
        redis_client = cache.get_redis_client()
        if redis_client:
            redis_client.ping()
        
        return {
            "status": "ready", 
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "not_ready", 
            "error": str(e), 
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.get("/liveness")
def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Checks if the application is alive and should not be restarted.
    """
    return {
        "status": "alive", 
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
