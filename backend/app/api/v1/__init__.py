from fastapi import APIRouter
from .sync_core import router as sync_router
# Note: v1 is now intended to only expose synchronous (legacy) endpoints.
# Async routers have been moved into api.v2. Keep v1 focused on sync routes.

router = APIRouter()

# Include sync router first for v1 (legacy sync endpoints)
router.include_router(sync_router)

# No async routers included here; v1 is sync-only.


@router.get("/info")
def api_v1_info():
    # Provide a simple listing of important Group 4 endpoints for test introspection
    return {
        "version": "v1",
        "description": "ReactAdmin-Refine Backend API v1 (sync/legacy endpoints)",
        "note": "Async endpoints were moved to /api/v2; call /api/v1 for legacy sync endpoints",
        # Provide a mapping so tests can detect which endpoints have async
        # implementations (we mark them with a small rocket emoji).
        "endpoints": {
            "health": "/api/v1/health",
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "roles": "/api/v1/roles",
            # Tenants and audit are implemented as async v2 endpoints
            "tenants": "🚀 /api/v2/tenants",
            "audit": "🚀 /api/v2/audit-logs",
            "cache": "/api/v1/cache"
        }
    }
