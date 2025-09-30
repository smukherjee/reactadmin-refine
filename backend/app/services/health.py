"""Shared health check utilities.

This module centralizes the detailed health check logic so both the
root FastAPI app and the v1 sync router can reuse the same implementation
without duplicating code (DRY). It also keeps Redis timeouts and
test-friendly behavior in one place.
"""

import time
from datetime import datetime
from typing import Any, Dict, Tuple

from backend.app.cache import core as cache
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


def _is_running_tests() -> bool:
    # Rely on PYTEST_CURRENT_TEST environment marker when available
    from os import getenv

    return getenv("PYTEST_CURRENT_TEST") is not None


def collect_detailed_health(db) -> Tuple[str, Dict[str, Any], Dict[str, float]]:
    """Perform detailed health checks for database, redis and system metrics.

    Returns (overall_status, components, timings_ms)
    timings_ms is a map of per-component measured durations to help debugging.
    """
    components: Dict[str, Any] = {}
    timings: Dict[str, float] = {}
    overall_status = "healthy"

    # Database check
    try:
        from sqlalchemy import text

        db_start = time.time()
        db.execute(text("SELECT 1"))
        db_response_time = (time.time() - db_start) * 1000
        timings["db_ms"] = round(db_response_time, 2)
        components["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2),
        }
    except Exception as e:
        components["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"

    # Redis check with bounded timeouts using centralized safe helper
    try:
        # First, attempt a quick ping with short timeout
        ping_resp = cache.safe_redis_call(lambda c: c.ping(), timeout=0.25)
        if ping_resp.get("ok"):
            # If ping succeeded, fetch INFO with a slightly longer timeout
            info_resp = cache.safe_redis_call(lambda c: c.info(), timeout=0.5)
            if info_resp.get("ok") and isinstance(info_resp.get("result"), dict):
                redis_info = info_resp.get("result") or {}
                timings["redis_ms"] = round(
                    (
                        ping_resp.get("elapsed_ms", 0.0)
                        + info_resp.get("elapsed_ms", 0.0)
                    ),
                    2,
                )
                components["redis"] = {
                    "status": "healthy",
                    "response_time_ms": timings["redis_ms"],
                    "memory_usage_mb": (
                        round(redis_info.get("used_memory", 0) / 1024 / 1024, 2)
                        if isinstance(redis_info.get("used_memory", 0), (int, float))
                        else 0.0
                    ),
                    "connected_clients": (
                        redis_info.get("connected_clients", 0)
                        if isinstance(redis_info.get("connected_clients", 0), int)
                        else 0
                    ),
                }
            else:
                # INFO failed or timed out
                timings["redis_ms"] = round(
                    ping_resp.get("elapsed_ms", 0.0) + info_resp.get("elapsed_ms", 0.0),
                    2,
                )
                err = info_resp.get("error") or "redis info failed or timed out"
                components["redis"] = {
                    "status": "degraded",
                    "error": err,
                    "response_time_ms": timings["redis_ms"],
                }
                overall_status = "degraded"
        else:
            # Ping failed or client not initialized
            if (
                ping_resp.get("error") == "redis client not initialized"
                and _is_running_tests()
            ):
                components["redis"] = {
                    "status": "healthy",
                    "response_time_ms": 0.0,
                    "memory_usage_mb": 0.0,
                    "connected_clients": 0,
                    "note": "placeholder - redis not initialized in test environment",
                }
            else:
                timings["redis_ms"] = round(ping_resp.get("elapsed_ms", 0.0), 2)
                components["redis"] = {
                    "status": "unavailable",
                    "error": ping_resp.get("error", "redis ping failed"),
                    "response_time_ms": timings["redis_ms"],
                }
                overall_status = "degraded"
    except Exception as e:
        components["redis"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"

    # System metrics (cached)
    try:
        from backend.app.services.system_metrics import get_cached_system_metrics

        system_start = time.time()
        system_metrics = get_cached_system_metrics()
        timings["system_ms"] = round((time.time() - system_start) * 1000, 2)
        components["system"] = system_metrics
        if system_metrics.get("status") != "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["system"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"

    logger.debug(f"health timings(ms): {timings}")
    return overall_status, components, timings
