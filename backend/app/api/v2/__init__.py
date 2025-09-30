from fastapi import APIRouter
from .async_tenants_audit import router as async_tenants_audit_router
from .async_users import router as async_users_router
from .async_auth import router as async_auth_router
from .async_user_mgmt import router as async_user_mgmt_router
from .async_roles import router as async_roles_router
from .async_cache_system import router as async_cache_system_router

router = APIRouter()

# Include all async routers under /api/v2
router.include_router(async_users_router)
router.include_router(async_auth_router)
router.include_router(async_user_mgmt_router)
router.include_router(async_roles_router)
router.include_router(async_tenants_audit_router)
router.include_router(async_cache_system_router)


@router.get('/info')
def api_v2_info():
    return {"version": "v2", "description": "Async API v2"}
