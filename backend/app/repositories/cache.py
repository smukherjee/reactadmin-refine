"""Async cache repository for cache management operations.

This module provides async cache operations including cache status,
clearing, statistics, and health monitoring.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
import time
from datetime import datetime

from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class AsyncCacheRepository:
    """Async repository for cache management operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def _get_redis_client(self):
        """Get async Redis client."""
        try:
            from backend.app.cache.async_redis import get_async_redis_client
            redis_client = await get_async_redis_client()
            if not redis_client:
                raise RuntimeError("Redis client not available")
            return redis_client
        except Exception as e:
            logger.error(f"Failed to get Redis client: {e}")
            raise
    
    async def get_cache_status(self) -> Dict[str, Any]:
        """Get comprehensive cache status and statistics."""
        try:
            redis = await self._get_redis_client()
            
            # Get basic Redis info
            redis_info = await redis.info()
            db_size = await redis.dbsize()
            
            # Test connection latency
            latency_start = time.time()
            await redis.ping()
            latency = (time.time() - latency_start) * 1000  # ms
            
            # Extract key metrics
            memory_used = redis_info.get("used_memory", 0)
            memory_used_human = redis_info.get("used_memory_human", "0B")
            uptime = redis_info.get("uptime_in_seconds", 0)
            version = redis_info.get("redis_version", "unknown")
            connected_clients = redis_info.get("connected_clients", 0)
            keyspace_hits = redis_info.get("keyspace_hits", 0)
            keyspace_misses = redis_info.get("keyspace_misses", 0)
            
            # Calculate hit rate
            hit_rate = 0.0
            total_requests = keyspace_hits + keyspace_misses
            if total_requests > 0:
                hit_rate = round((keyspace_hits / total_requests) * 100, 2)
            
            status = {
                "status": "healthy",
                "connected": True,
                "uptime_seconds": uptime,
                "redis_version": version,
                "total_keys": db_size,
                "memory_used": memory_used,
                "memory_used_human": memory_used_human,
                "latency_ms": round(latency, 2),
                "connected_clients": connected_clients,
                "keyspace_hits": keyspace_hits,
                "keyspace_misses": keyspace_misses,
                "hit_rate_percent": hit_rate,
                "last_checked": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Cache status retrieved: {db_size} keys, {latency:.2f}ms latency")
            return status
            
        except Exception as e:
            logger.error(f"Cache status check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    async def clear_cache(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """Clear cache entries, optionally by pattern."""
        try:
            redis = await self._get_redis_client()
            
            if pattern:
                # Clear by pattern
                keys = await redis.keys(pattern)
                if keys:
                    deleted_count = await redis.delete(*keys)
                else:
                    deleted_count = 0
                    
                # Successfully cleared cache by pattern
                
                logger.info(f"Cleared {deleted_count} cache keys matching pattern: {pattern}")
                
                return {
                    "status": "success",
                    "pattern": pattern,
                    "keys_deleted": deleted_count,
                    "message": f"Cleared {deleted_count} keys matching pattern '{pattern}'"
                }
            else:
                # Clear all cache
                await redis.flushdb()
                
                # Successfully cleared all cache
                
                logger.info("Cleared all cache entries")
                
                return {
                    "status": "success",
                    "pattern": "*",
                    "keys_deleted": "all",
                    "message": "Cleared all cache entries"
                }
                
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Cache clear operation failed"
            }
    
    async def get_cache_keys(self, pattern: str = "*", limit: int = 100) -> Dict[str, Any]:
        """Get cache keys matching a pattern."""
        try:
            redis = await self._get_redis_client()
            
            # Get keys matching pattern
            all_keys = await redis.keys(pattern)
            
            # Limit results and convert to strings
            keys = []
            for i, key in enumerate(all_keys):
                if i >= limit:
                    break
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                keys.append(key_str)
            
            result = {
                "pattern": pattern,
                "total_matches": len(all_keys),
                "returned": len(keys),
                "limit": limit,
                "keys": keys
            }
            
            logger.info(f"Retrieved {len(keys)} cache keys for pattern: {pattern}")
            return result
            
        except Exception as e:
            logger.error(f"Cache keys retrieval failed: {e}")
            return {
                "pattern": pattern,
                "error": str(e),
                "keys": []
            }
    
    async def set_cache_value(self, key: str, value: Any, ttl: Optional[int] = None) -> Dict[str, Any]:
        """Set a cache value with optional TTL."""
        try:
            redis = await self._get_redis_client()
            
            # Convert value to string if necessary
            if isinstance(value, (dict, list)):
                import json
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            # Set the value
            if ttl:
                await redis.setex(key, ttl, value_str)
            else:
                await redis.set(key, value_str)
            
            # Successfully set cache value
            
            logger.info(f"Set cache key '{key}' with TTL: {ttl}")
            
            return {
                "status": "success",
                "key": key,
                "ttl": ttl,
                "message": f"Successfully set cache key '{key}'"
            }
            
        except Exception as e:
            logger.error(f"Cache set value failed: {e}")
            return {
                "status": "error",
                "key": key,
                "error": str(e),
                "message": f"Failed to set cache key '{key}'"
            }
    
    async def get_cache_value(self, key: str) -> Dict[str, Any]:
        """Get a cache value by key."""
        try:
            redis = await self._get_redis_client()
            
            # Get the value
            value = await redis.get(key)
            ttl = await redis.ttl(key)
            
            if value is None:
                return {
                    "status": "not_found",
                    "key": key,
                    "value": None,
                    "message": f"Key '{key}' not found in cache"
                }
            
            # Try to decode as JSON, fall back to string
            try:
                import json
                decoded_value = json.loads(value.decode())
            except (json.JSONDecodeError, AttributeError):
                decoded_value = value.decode() if isinstance(value, bytes) else str(value)
            
            # Successfully retrieved cache value
            
            return {
                "status": "success",
                "key": key,
                "value": decoded_value,
                "ttl": ttl if ttl > 0 else None,
                "message": f"Successfully retrieved cache key '{key}'"
            }
            
        except Exception as e:
            logger.error(f"Cache get value failed: {e}")
            return {
                "status": "error",
                "key": key,
                "error": str(e),
                "message": f"Failed to get cache key '{key}'"
            }
    
    async def delete_cache_key(self, key: str) -> Dict[str, Any]:
        """Delete a specific cache key."""
        try:
            redis = await self._get_redis_client()
            
            # Delete the key
            deleted = await redis.delete(key)
            
            # Successfully deleted cache key
            
            if deleted:
                logger.info(f"Deleted cache key: {key}")
                return {
                    "status": "success",
                    "key": key,
                    "deleted": True,
                    "message": f"Successfully deleted cache key '{key}'"
                }
            else:
                return {
                    "status": "not_found",
                    "key": key,
                    "deleted": False,
                    "message": f"Cache key '{key}' not found"
                }
                
        except Exception as e:
            logger.error(f"Cache delete key failed: {e}")
            return {
                "status": "error",
                "key": key,
                "error": str(e),
                "message": f"Failed to delete cache key '{key}'"
            }


async def get_cache_repository(session: AsyncSession) -> AsyncCacheRepository:
    """Factory function to create AsyncCacheRepository instance."""
    return AsyncCacheRepository(session)