"""Async API endpoints for user management.

This demonstrates how to use async database operations with the new repository pattern.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.core import get_async_db
from backend.app.repositories import AsyncUserRepository, get_user_repository
from backend.app.schemas.core import UserOut, UserCreate, UserUpdate
from backend.app.auth.core import get_current_user
from backend.app.models.core import User
from backend.app.crud.core import pwd_context
import uuid

router = APIRouter(prefix="/async/users", tags=["async-users"])


@router.get("/me", response_model=UserOut)
async def get_current_user_async(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get current user using async database operations."""
    repo = await get_user_repository(db)
    user = await repo.get_by_id(uuid.UUID(str(current_user.id)))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user_async(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
    if str(user.client_id) != str(current_user.client_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return user


@router.get("/", response_model=List[UserOut])
async def list_users_async(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List users for current tenant using async database operations."""
    if limit > 100:
        limit = 100
    
    repo = await get_user_repository(db)
    users = await repo.list_by_tenant(uuid.UUID(str(current_user.client_id)), skip=skip, limit=limit)
    return users


@router.post("/", response_model=UserOut)
async def create_user_async(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new user using async database operations."""
    # Ensure user is creating in their own tenant
    if user_data.client_id != current_user.client_id:
        raise HTTPException(status_code=403, detail="Cannot create user for different tenant")
    
    repo = await get_user_repository(db)
    
    # Check if user with email already exists
    existing_user = await repo.get_by_email(user_data.email, user_data.client_id)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
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
    db: AsyncSession = Depends(get_async_db)
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
    if str(existing_user.client_id) != str(current_user.client_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    updated_user = await repo.update(user_uuid, user_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return updated_user


@router.delete("/{user_id}")
async def delete_user_async(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
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
    if str(existing_user.client_id) != str(current_user.client_id):
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
    db: AsyncSession = Depends(get_async_db)
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
    if str(existing_user.client_id) != str(current_user.client_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    permissions = await repo.get_user_permissions(user_uuid)
    return {"user_id": user_id, "permissions": permissions}