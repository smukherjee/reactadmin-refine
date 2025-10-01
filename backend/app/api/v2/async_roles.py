"""Async role and permission API routes.

This module provides async FastAPI routes for role management and
permission-protected operations.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.async_auth import (
    get_current_user_async,
    require_permission_async,
    validate_tenant_access_async,
)
from backend.app.core.logging import get_logger
from backend.app.db.core import get_async_db
from backend.app.models.core import User
from backend.app.repositories.roles import AsyncRoleRepository, get_role_repository
from backend.app.schemas.core import RoleCreate, RoleOut

logger = get_logger(__name__)

router = APIRouter(tags=["Roles & Permissions"])


@router.post("/roles", response_model=RoleOut)
async def async_create_role(
    role: RoleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("roles:create")),
):
    """Create a new role (async)."""
    try:
        # Validate tenant_id is provided
        if role.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id required"
            )

        # Only allow creating roles within the same tenant
        validate_tenant_access_async(current_user, str(role.tenant_id))

        role_repo = await get_role_repository(db)

        # Check if role name already exists in tenant
        existing_role = await role_repo.get_by_name(role.name, role.tenant_id)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{role.name}' already exists in this tenant",
            )

        # Create role
        new_role = await role_repo.create(role)

        logger.info(
            f"Created role {new_role.id} '{new_role.name}' for tenant {role.tenant_id}"
        )
        return new_role

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Role creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role creation failed",
        )


@router.get("/roles", response_model=List[RoleOut])
async def async_list_roles(
    tenant_id: str = Query(..., description="Tenant/Client ID to filter roles"),
    skip: int = Query(0, ge=0, description="Number of roles to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of roles to return"
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    """List roles by tenant (async)."""
    try:
        # Tenant-scoped access validation
        validate_tenant_access_async(current_user, tenant_id)

        role_repo = await get_role_repository(db)

        # Convert tenant_id to UUID
        try:
            client_uuid = uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format",
            )

        # Get roles by tenant
        roles = await role_repo.list_by_tenant(client_uuid, skip=skip, limit=limit)

        logger.info(f"Retrieved {len(roles)} roles for tenant {tenant_id}")
        return roles

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List roles error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve roles",
        )


@router.post("/roles/{role_id}/assign-test")
async def async_assign_role_test(
    role_id: str,
    user_id: str = Query(..., description="User ID to assign role to"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("assign:role")),
):
    """Test role assignment endpoint with RBAC check (async)."""
    try:
        role_repo = await get_role_repository(db)

        # Convert string UUIDs
        try:
            role_uuid = uuid.UUID(role_id)
            user_uuid = uuid.UUID(user_id)
            assigned_by_uuid = uuid.UUID(str(current_user.id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format"
            )

        # Assign role (includes tenant validation)
        success = await role_repo.assign_role_to_user(
            user_id=user_uuid, role_id=role_uuid, assigned_by=assigned_by_uuid
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User/role not found or not in same tenant",
            )

        logger.info(
            f"Test assignment: role {role_id} assigned to user {user_id} by {current_user.id}"
        )
        return {
            "message": "Role assigned successfully (test endpoint)",
            "role_id": role_id,
            "user_id": user_id,
            "assigned_by": str(current_user.id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Role assignment test error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role assignment test failed",
        )


@router.get("/protected/resource")
async def async_protected_resource(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    allowed: bool = Depends(require_permission_async("read:protected")),
):
    """Example protected endpoint requiring specific permission (async)."""
    try:
        # Get user permissions for demonstration
        role_repo = await get_role_repository(db)
        user_uuid = uuid.UUID(str(current_user.id))
        user_permissions = await role_repo.get_user_permissions(user_uuid)

        logger.info(f"User {current_user.id} accessed protected resource")

        return {
            "status": "ok",
            "message": "Access granted to protected resource",
            "user": str(current_user.id),
            "user_email": current_user.email,
            "tenant": str(current_user.tenant_id),
            "permissions": list(user_permissions),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Protected resource access error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Protected resource access failed",
        )


@router.get("/roles/{role_id}")
async def async_get_role(
    role_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
):
    """Get role by ID (async)."""
    try:
        role_repo = await get_role_repository(db)

        # Convert role_id to UUID
        try:
            role_uuid = uuid.UUID(role_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_id format"
            )

        # Get role
        role = await role_repo.get_by_id(role_uuid)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        # Validate tenant access
        validate_tenant_access_async(current_user, str(role.tenant_id))

        return role

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role",
        )


@router.delete("/roles/{role_id}")
async def async_delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("roles:delete")),
):
    """Delete role by ID (async)."""
    try:
        role_repo = await get_role_repository(db)

        # Convert role_id to UUID
        try:
            role_uuid = uuid.UUID(role_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_id format"
            )

        # Check if role exists and validate tenant access
        role = await role_repo.get_by_id(role_uuid)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        validate_tenant_access_async(current_user, str(role.tenant_id))

        # Delete role
        success = await role_repo.delete(role_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        logger.info(f"Deleted role {role_id}")
        return {"message": "Role deleted successfully", "role_id": role_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role deletion failed",
        )
