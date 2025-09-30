"""Async user management API routes.

This module provides async FastAPI routes for user management operations,
including user registration, listing, and role assignment.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger
from backend.app.core.security import get_password_hash
from backend.app.db.core import get_async_db
from backend.app.repositories import get_user_repository
from backend.app.schemas.core import UserCreate, UserOut, UserUpdate

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserOut)
async def async_register_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Register a new user (async)."""
    try:
        user_repo = await get_user_repository(db)

        # Check if user already exists (idempotent)
        existing_user = await user_repo.get_by_email(user.email, user.client_id)
        if existing_user:
            logger.info(f"User {user.email} already exists, returning existing user")
            return existing_user

        # Hash password
        hashed_password = get_password_hash(user.password)

        # Create user
        new_user = await user_repo.create(user, hashed_password)

        logger.info(f"Created new user {new_user.id} with email {user.email}")
        return new_user

    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed",
        )


@router.get("", response_model=List[UserOut])
async def async_list_users(
    client_id: str = Query(..., description="Tenant/Client ID to filter users"),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of users to return"
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """List users by tenant (async)."""
    try:
        user_repo = await get_user_repository(db)

        # Convert client_id to UUID
        try:
            client_uuid = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid client_id format",
            )

        # Get users by tenant
        users = await user_repo.list_by_tenant(client_uuid, skip=skip, limit=limit)

        logger.info(f"Retrieved {len(users)} users for tenant {client_id}")
        return users

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users",
        )


@router.post("/{user_id}/roles")
async def async_assign_role(
    user_id: str,
    role_id: str = Query(..., description="Role ID to assign"),
    assigned_by: Optional[str] = Query(
        None, description="ID of user making the assignment"
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """Assign a role to a user (async)."""
    try:
        user_repo = await get_user_repository(db)

        # Convert string UUIDs
        try:
            user_uuid = uuid.UUID(user_id)
            role_uuid = uuid.UUID(role_id)
            assigned_by_uuid = uuid.UUID(assigned_by) if assigned_by else None
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format"
            )

        # Assign role
        success = await user_repo.assign_role(
            user_id=user_uuid, role_id=role_uuid, assigned_by=assigned_by_uuid
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or role not available in user's tenant",
            )

        logger.info(f"Successfully assigned role {role_id} to user {user_id}")
        return {
            "message": "Role assigned successfully",
            "user_id": user_id,
            "role_id": role_id,
            "assigned_by": assigned_by,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Role assignment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role assignment failed",
        )


@router.get("/{user_id}")
async def async_get_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Get user by ID (async)."""
    try:
        user_repo = await get_user_repository(db)

        # Convert user_id to UUID
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format"
            )

        # Get user
        user = await user_repo.get_by_id(user_uuid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user",
        )


@router.put("/{user_id}", response_model=UserOut)
async def async_update_user(
    user_id: str,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Update user by ID (async)."""
    try:
        user_repo = await get_user_repository(db)

        # Convert user_id to UUID
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format"
            )

        # Update user
        updated_user = await user_repo.update(user_uuid, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        logger.info(f"Updated user {user_id}")
        return updated_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed",
        )


@router.delete("/{user_id}")
async def async_delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete user by ID (async)."""
    try:
        user_repo = await get_user_repository(db)

        # Convert user_id to UUID
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format"
            )

        # Delete user
        success = await user_repo.delete(user_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        logger.info(f"Deleted user {user_id}")
        return {"message": "User deleted successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deletion failed",
        )
