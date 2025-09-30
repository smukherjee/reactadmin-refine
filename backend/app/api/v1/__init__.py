from fastapi import APIRouter
from .async_users import router as async_users_router
from .async_auth import router as async_auth_router
from .async_user_mgmt import router as async_user_mgmt_router
from .async_roles import router as async_roles_router
from .async_tenants_audit import router as async_tenants_audit_router
from .async_cache_system import router as async_cache_system_router

router = APIRouter()

# Include async routers
router.include_router(async_users_router)
router.include_router(async_auth_router)
router.include_router(async_user_mgmt_router)
router.include_router(async_roles_router)
router.include_router(async_tenants_audit_router)
router.include_router(async_cache_system_router)

# Note: The main API endpoints are implemented in backend.app.main.core
# This v1 router can be used for future API versioning if needed

@router.get("/info")
def api_v1_info():
    """
    API v1 information endpoint.
    """
    return {
        "version": "v1",
        "description": "ReactAdmin-Refine Backend API v1",
        "endpoints": {
            "health": "/health, /health/detailed, /readiness, /liveness, /metrics",
            "auth": "🚀 /auth/login, /auth/refresh, /auth/logout, /auth/sessions, /auth/logout-all (ASYNC)",
            "users": "🚀 /users, /users/{user_id}, /users/{user_id}/roles (ASYNC)",
            "roles": "🚀 /roles, /roles/{role_id}, /roles/{role_id}/assign-test (ASYNC)",
            "protected": "🚀 /protected/resource (ASYNC)",
            "legacy_users": "/users (sync version still available)", 
            "legacy_roles": "/roles (sync version still available)",
            "tenants": "🚀 /tenants, /tenants/{tenant_id} (ASYNC)", 
            "audit": "🚀 /audit-logs, /audit-logs/statistics, /audit-logs/cleanup (ASYNC)",
            "cache": "🚀 /cache/status, /cache/clear, /cache/keys, /cache/set, /cache/get, /cache/delete (ASYNC)",
            "system": "🚀 /system/health, /system/database, /system/metrics, /system/performance, /system/healthcheck (ASYNC)"
        }
    }
