"""Async repository for user operations.

This module provides async database operations for user management.
It serves as an example of migrating from sync to async database operations.
"""

import time
import uuid
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import get_logger, log_database_operation
from backend.app.models.core import Role, User, UserRole
from backend.app.schemas.core import UserCreate, UserUpdate

logger = get_logger(__name__)


class AsyncUserRepository:
    """Async repository for user database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        start_time = time.time()
        try:
            stmt = (
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.roles), selectinload(User.tenant))
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "users", duration_ms)

            return user
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            raise

    async def get_by_email(self, email: str, tenant_id: uuid.UUID) -> Optional[User]:
        """Get user by email within tenant."""
        start_time = time.time()
        try:
            stmt = (
                select(User)
                .where(User.email == email, User.tenant_id == tenant_id)
                .options(selectinload(User.roles))
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "users", duration_ms)

            return user
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise

    async def create(self, user_data: UserCreate, hashed_password: str) -> User:
        """Create a new user with pre-hashed password."""
        start_time = time.time()
        try:
            user = User(
                email=user_data.email,
                password_hash=hashed_password,
                tenant_id=user_data.tenant_id,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                is_active=True,
                is_verified=False,
            )

            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("INSERT", "users", duration_ms)

            logger.info(f"Created user {user.id} with email {user.email}")
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating user: {e}")
            raise

    async def update(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[User]:
        """Update user by ID."""
        start_time = time.time()
        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(**user_data.model_dump(exclude_unset=True))
                .returning(User)
            )
            result = await self.session.execute(stmt)
            updated_user = result.scalar_one_or_none()

            if updated_user:
                await self.session.commit()
                await self.session.refresh(updated_user)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("UPDATE", "users", duration_ms)

            return updated_user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise

    async def delete(self, user_id: uuid.UUID) -> bool:
        """Delete user by ID."""
        start_time = time.time()
        try:
            stmt = delete(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            await self.session.commit()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "users", duration_ms)

            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """List users by tenant with pagination."""
        start_time = time.time()
        try:
            stmt = (
                select(User)
                .where(User.tenant_id == tenant_id)
                .options(selectinload(User.roles))
                .offset(skip)
                .limit(limit)
                .order_by(User.created_at.desc())
            )
            result = await self.session.execute(stmt)
            users = result.scalars().all()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "users", duration_ms, len(users))

            return list(users)
        except Exception as e:
            logger.error(f"Error listing users for tenant {tenant_id}: {e}")
            raise

    async def get_user_permissions(self, user_id: uuid.UUID) -> List[str]:
        """Get all permissions for a user through their roles."""
        start_time = time.time()
        try:
            stmt = (
                select(User).where(User.id == user_id).options(selectinload(User.roles))
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return []

            permissions = set()
            for role in user.roles:
                # Role.permissions is a JSON column containing list of permission strings
                if role.permissions:
                    for permission in role.permissions:
                        permissions.add(permission)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "users_roles_permissions", duration_ms)

            return list(permissions)
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {e}")
            raise

    async def assign_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: Optional[uuid.UUID] = None,
    ) -> bool:
        """Assign a role to a user."""
        start_time = time.time()
        try:
            # Check if user exists
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found for role assignment")
                return False

            # Check if role exists and belongs to same tenant
            role_stmt = select(Role).where(
                Role.id == role_id, Role.tenant_id == user.tenant_id
            )
            role_result = await self.session.execute(role_stmt)
            role = role_result.scalar_one_or_none()

            if not role:
                logger.warning(
                    f"Role {role_id} not found or not in same tenant as user {user_id}"
                )
                return False

            # Check if role is already assigned
            existing_stmt = select(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
            existing_result = await self.session.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                logger.info(f"Role {role_id} already assigned to user {user_id}")
                return True

            # Create new role assignment
            user_role = UserRole(
                user_id=user_id, role_id=role_id, assigned_by=assigned_by
            )

            self.session.add(user_role)
            await self.session.commit()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("INSERT", "user_roles", duration_ms)

            logger.info(f"Assigned role {role_id} to user {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error assigning role {role_id} to user {user_id}: {e}")
            raise


async def get_user_repository(session: AsyncSession) -> AsyncUserRepository:
    """Factory function to create user repository."""
    return AsyncUserRepository(session)


from .audit import AsyncAuditRepository, get_audit_repository

# Import async repositories for easy access
from .auth import AsyncAuthRepository, get_auth_repository
from .cache import AsyncCacheRepository, get_cache_repository
from .roles import AsyncRoleRepository, get_role_repository
from .sessions import AsyncSessionRepository, get_session_repository
from .system import AsyncSystemRepository, get_system_repository
from .tenants import AsyncTenantRepository, get_tenant_repository

__all__ = [
    "AsyncUserRepository",
    "get_user_repository",
    "AsyncAuthRepository",
    "get_auth_repository",
    "AsyncSessionRepository",
    "get_session_repository",
    "AsyncRoleRepository",
    "get_role_repository",
    "AsyncTenantRepository",
    "get_tenant_repository",
    "AsyncAuditRepository",
    "get_audit_repository",
    "AsyncCacheRepository",
    "get_cache_repository",
    "AsyncSystemRepository",
    "get_system_repository",
]
