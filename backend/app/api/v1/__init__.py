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
        "description": "ReactAdmin-Refine Backend API v1",
        "endpoints": {
            "tenants": "🚀 GET /api/v1/tenants, GET /api/v1/tenants/{id} (async)",
            "audit": "🚀 POST /api/v1/audit-logs, GET /api/v1/audit-logs, GET /api/v1/audit-logs/statistics (async)"
        }
    }
