from fastapi import APIRouter

router = APIRouter()

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
            "auth": "/auth/login, /auth/refresh, /auth/logout, /auth/sessions, /auth/logout-all",
            "users": "/users, /users/{user_id}/roles",
            "roles": "/roles, /roles/{role_id}/assign-test",
            "tenants": "/tenants",
            "cache": "/cache/status, /cache/clear",
            "audit": "/audit-logs",
            "protected": "/protected/resource"
        }
    }
