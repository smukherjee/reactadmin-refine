"""Async API endpoints for user management.

This demonstrates how to use async database operations with the new repository pattern.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.core import get_current_user
from backend.app.crud.core import pwd_context
from backend.app.db.core import get_async_db
from backend.app.models.core import User
from backend.app.repositories import get_user_repository
from backend.app.repositories.tenants import get_tenant_repository
from backend.app.schemas.core import UserCreate, UserOut, UserUpdate, UserWithTenantOut

router = APIRouter(prefix="/async/users", tags=["async-users"])


@router.get("/me", response_model=UserWithTenantOut)
async def get_current_user_async(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get current user using async database operations."""
    repo = await get_user_repository(db)
    user = await repo.get_by_id(uuid.UUID(str(current_user.id)))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has superadmin role
    is_superadmin = any(role.name == "superadmin" for role in user.roles) if user.roles else False
    
    # Get available tenants based on role
    if is_superadmin:
        # Superadmin gets access to all tenants
        tenant_repo = await get_tenant_repository(db)
        all_tenants = await tenant_repo.list_all()
        available_tenants = all_tenants
    else:
        # Regular users only get their own tenant
        available_tenants = [user.tenant]
    
    # Convert to dict and add tenant fields
    user_dict = user.__dict__.copy()
    user_dict['current_tenant'] = user.tenant
    user_dict['available_tenants'] = available_tenants
    
    return user_dict


@router.get("/{user_id}", response_model=UserOut)
async def get_user_async(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get user by ID using async database operations."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    repo = await get_user_repository(db)
    user = await repo.get_by_id(user_uuid)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure user can only access users from same tenant
    if str(user.tenant_id) != str(current_user.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return user


@router.get("/", response_model=List[UserOut])
async def list_users_async(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List users for current tenant using async database operations."""
    if limit > 100:
        limit = 100

    repo = await get_user_repository(db)
    users = await repo.list_by_tenant(
        uuid.UUID(str(current_user.tenant_id)), skip=skip, limit=limit
    )
    return users


@router.post("/", response_model=UserOut)
async def create_user_async(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new user using async database operations."""
    # Ensure user is creating in their own tenant
    if user_data.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=403, detail="Cannot create user for different tenant"
        )

    repo = await get_user_repository(db)

    # Check if user with email already exists
    existing_user = await repo.get_by_email(user_data.email, user_data.tenant_id)
    if existing_user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    # Hash password
    hashed_password = pwd_context.hash(user_data.password)

    # Create user
    user = await repo.create(user_data, hashed_password)
    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user_async(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update user using async database operations."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    repo = await get_user_repository(db)

    # Get existing user to check tenant
    existing_user = await repo.get_by_id(user_uuid)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure user can only update users from same tenant
    if str(existing_user.tenant_id) != str(current_user.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    updated_user = await repo.update(user_uuid, user_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return updated_user


@router.delete("/{user_id}")
async def delete_user_async(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete user using async database operations."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    repo = await get_user_repository(db)

    # Get existing user to check tenant
    existing_user = await repo.get_by_id(user_uuid)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure user can only delete users from same tenant
    if str(existing_user.tenant_id) != str(current_user.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Don't allow users to delete themselves
    if user_uuid == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    success = await repo.delete(user_uuid)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}


@router.get("/{user_id}/permissions")
async def get_user_permissions_async(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get user permissions using async database operations."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    repo = await get_user_repository(db)

    # Get existing user to check tenant
    existing_user = await repo.get_by_id(user_uuid)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure user can only access users from same tenant
    if str(existing_user.tenant_id) != str(current_user.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    permissions = await repo.get_user_permissions(user_uuid)
    return {"user_id": user_id, "permissions": permissions}
