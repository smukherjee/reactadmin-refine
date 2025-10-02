"""Async authentication helpers and dependencies.

This module provides async versions of authentication dependencies,
including user retrieval and permission checking for async endpoints.
"""

import uuid
from typing import Any, Dict, Set

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.core import _get_payload_from_request
from backend.app.core.logging import get_logger
from backend.app.core.security import decode_token
from backend.app.crud import core as crud_core
from backend.app.db.core import get_async_db
from backend.app.models.core import User
from backend.app.repositories.roles import AsyncRoleRepository, get_role_repository

# v2 async endpoints should not use sync fallbacks; tests should call /api/v1 for
# sync behavior or configure an async test DB. Remove threadpool fallbacks.

logger = get_logger(__name__)


async def get_current_user_async(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    payload: Dict[str, Any] = Depends(_get_payload_from_request),
) -> User:
    """Async version: Return the current user object based on the token payload.

    Raises 401 if token is invalid or user not found.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Convert to UUID
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")

    # Get user from database asynchronously
    try:
        stmt = select(User).where(User.id == user_uuid)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Do not attempt sync fallbacks in v2. If the async DB cannot see
            # the user, treat it as not found. Tests should create users via
            # async repositories or call the /api/v1 sync endpoints.
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def require_permission_async(permission: str):
    """Async dependency factory that raises 403 if current user lacks the permission."""

    async def _checker(
        request: Request,
        current_user: User = Depends(get_current_user_async),
        db: AsyncSession = Depends(get_async_db),
    ):
        try:
            role_repo = await get_role_repository(db)
            user_id = uuid.UUID(str(current_user.id))
            permissions = await role_repo.get_user_permissions(user_id)
            # Do not perform sync fallback permission checks in v2. Require
            # permissions to be resolvable via async repositories.
            # Check for specific permission or wildcard "*" permission
            if permission not in permissions and "*" not in permissions:
                logger.warning(f"User {current_user.id} lacks permission: {permission}")
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            logger.debug(f"User {current_user.id} has permission: {permission}")
            return True
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error checking permission {permission} for user {current_user.id}: {e}"
            )
            raise HTTPException(status_code=500, detail="Permission check failed")

    return _checker


async def get_user_permissions_async(user_id: uuid.UUID, db: AsyncSession) -> Set[str]:
    """Get all permissions for a user (async helper function)."""
    try:
        role_repo = await get_role_repository(db)
        return await role_repo.get_user_permissions(user_id)
    except Exception as e:
        logger.error(f"Error getting permissions for user {user_id}: {e}")
        return set()


def validate_tenant_access_async(current_user: User, requested_tenant_id: str):
    """Validate that the current user can access the requested tenant."""
    # Check if user has superadmin role - superadmin can access any tenant
    is_superadmin = any(role.name == "superadmin" for role in current_user.roles) if current_user.roles else False
    
    if not is_superadmin and str(current_user.tenant_id) != str(requested_tenant_id):
        logger.warning(
            f"User {current_user.id} attempted to access tenant {requested_tenant_id}, but belongs to {current_user.tenant_id}"
        )
        raise HTTPException(
            status_code=403, detail="Forbidden: Cannot access different tenant"
        )
