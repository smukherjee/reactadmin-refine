"""Async cache and system monitoring API routes.

This module provides async FastAPI routes for cache management and 
system monitoring operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import uuid

from backend.app.db.core import get_async_db
from backend.app.repositories.cache import get_cache_repository, AsyncCacheRepository
from backend.app.repositories.system import get_system_repository, AsyncSystemRepository
from backend.app.models.core import User
from backend.app.auth.async_auth import (
    get_current_user_async, 
    require_permission_async
)
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Cache & System"])


# ================================
# CACHE MANAGEMENT ENDPOINTS
# ================================

@router.get("/cache/status")
async def async_get_cache_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("cache:read"))
):
    """Get comprehensive cache status and statistics (async)."""
    try:
        cache_repo = await get_cache_repository(db)
        
        cache_status = await cache_repo.get_cache_status()
        
        logger.info(f"Cache status retrieved by user {current_user.id}")
        return cache_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache status"
        )


@router.post("/cache/clear")
async def async_clear_cache(
    pattern: Optional[str] = Query(None, description="Pattern to match keys for deletion (optional)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("cache:admin"))
):
    """Clear cache entries, optionally by pattern (async) - admin only."""
    try:
        cache_repo = await get_cache_repository(db)
        
        result = await cache_repo.clear_cache(pattern)
        
        logger.info(f"Cache cleared by admin {current_user.id}, pattern: {pattern}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get("/cache/keys")
async def async_get_cache_keys(
    pattern: str = Query("*", description="Pattern to match keys"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of keys to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("cache:read"))
):
    """Get cache keys matching a pattern (async)."""
    try:
        cache_repo = await get_cache_repository(db)
        
        result = await cache_repo.get_cache_keys(pattern, limit)
        
        logger.info(f"Cache keys retrieved by user {current_user.id}, pattern: {pattern}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache keys retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache keys"
        )


@router.post("/cache/set")
async def async_set_cache_value(
    key: str = Query(..., description="Cache key"),
    value: str = Query(..., description="Cache value"),
    ttl: Optional[int] = Query(None, description="Time to live in seconds"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("cache:write"))
):
    """Set a cache key-value pair with optional TTL (async)."""
    try:
        cache_repo = await get_cache_repository(db)
        
        result = await cache_repo.set_cache_value(key, value, ttl)
        
        logger.info(f"Cache key '{key}' set by user {current_user.id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set cache value"
        )


@router.get("/cache/get")
async def async_get_cache_value(
    key: str = Query(..., description="Cache key to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("cache:read"))
):
    """Get a cache value by key (async)."""
    try:
        cache_repo = await get_cache_repository(db)
        
        result = await cache_repo.get_cache_value(key)
        
        logger.info(f"Cache key '{key}' retrieved by user {current_user.id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cache value"
        )


@router.delete("/cache/delete")
async def async_delete_cache_key(
    key: str = Query(..., description="Cache key to delete"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("cache:write"))
):
    """Delete a specific cache key (async)."""
    try:
        cache_repo = await get_cache_repository(db)
        
        result = await cache_repo.delete_cache_key(key)
        
        logger.info(f"Cache key '{key}' deleted by user {current_user.id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cache key"
        )


# ================================
# SYSTEM MONITORING ENDPOINTS
# ================================

@router.get("/system/health")
async def async_get_system_health(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("system:read"))
):
    """Get comprehensive system health metrics (async)."""
    try:
        system_repo = await get_system_repository(db)
        
        health = await system_repo.get_system_health()
        
        logger.info(f"System health retrieved by user {current_user.id}")
        return health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System health error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health"
        )


@router.get("/system/database")
async def async_get_database_health(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("system:read"))
):
    """Get database health and performance metrics (async)."""
    try:
        system_repo = await get_system_repository(db)
        
        db_health = await system_repo.get_database_health()
        
        logger.info(f"Database health retrieved by user {current_user.id}")
        return db_health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database health error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database health"
        )


@router.get("/system/metrics")
async def async_get_application_metrics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("system:read"))
):
    """Get application-specific metrics and statistics (async)."""
    try:
        system_repo = await get_system_repository(db)
        
        metrics = await system_repo.get_application_metrics()
        
        logger.info(f"Application metrics retrieved by user {current_user.id}")
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Application metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application metrics"
        )


@router.get("/system/performance")
async def async_get_performance_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("system:read"))
):
    """Get comprehensive performance statistics (async)."""
    try:
        system_repo = await get_system_repository(db)
        
        stats = await system_repo.get_performance_stats()
        
        logger.info(f"Performance stats retrieved by user {current_user.id}")
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Performance stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance statistics"
        )


@router.get("/system/healthcheck")
async def async_run_health_check(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("system:read"))
):
    """Run comprehensive health check of all system components (async)."""
    try:
        system_repo = await get_system_repository(db)
        
        health_check = await system_repo.run_health_check()
        
        logger.info(f"Health check completed by user {current_user.id}")
        return health_check
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run health check"
        )