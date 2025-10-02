"""Async repository for role operations.

This module provides async database operations for role management,
including role creation, listing, and permission handling.
"""

import time
import uuid
from typing import List, Optional, Set

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import get_logger, log_database_operation
from backend.app.models.core import Role, User, UserRole
from backend.app.schemas.core import RoleCreate, RoleOut

logger = get_logger(__name__)


class AsyncRoleRepository:
    """Async repository for role database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        """Get role by ID."""
        start_time = time.time()
        try:
            stmt = select(Role).where(Role.id == role_id)
            result = await self.session.execute(stmt)
            role = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "roles", duration_ms)

            return role
        except Exception as e:
            logger.error(f"Error getting role by ID {role_id}: {e}")
            raise

    async def get_by_name(self, name: str, tenant_id: uuid.UUID) -> Optional[Role]:
        """Get role by name within tenant."""
        start_time = time.time()
        try:
            stmt = select(Role).where(Role.name == name, Role.tenant_id == tenant_id)
            result = await self.session.execute(stmt)
            role = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "roles", duration_ms)

            return role
        except Exception as e:
            logger.error(f"Error getting role by name {name}: {e}")
            raise

    async def create(self, role_data: RoleCreate) -> Role:
        """Create a new role."""
        start_time = time.time()
        try:
            role = Role(
                name=role_data.name,
                description=role_data.description or "",
                permissions=role_data.permissions or [],
                tenant_id=role_data.tenant_id,
            )

            self.session.add(role)
            await self.session.commit()
            await self.session.refresh(role)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("INSERT", "roles", duration_ms)

            logger.info(f"Created role {role.id} with name {role.name}")
            return role
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating role: {e}")
            raise

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Role]:
        """List roles by tenant with pagination."""
        start_time = time.time()
        try:
            stmt = (
                select(Role)
                .where(Role.tenant_id == tenant_id)
                .offset(skip)
                .limit(limit)
                .order_by(Role.created_at.desc())
            )
            result = await self.session.execute(stmt)
            roles = result.scalars().all()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "roles", duration_ms, len(roles))

            return list(roles)
        except Exception as e:
            logger.error(f"Error listing roles for tenant {tenant_id}: {e}")
            raise

    async def update(self, role_id: uuid.UUID, updates: dict) -> Optional[Role]:
        """Update role by ID."""
        start_time = time.time()
        try:
            stmt = (
                update(Role).where(Role.id == role_id).values(**updates).returning(Role)
            )
            result = await self.session.execute(stmt)
            updated_role = result.scalar_one_or_none()

            if updated_role:
                await self.session.commit()
                await self.session.refresh(updated_role)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("UPDATE", "roles", duration_ms)

            return updated_role
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating role {role_id}: {e}")
            raise

    async def delete(self, role_id: uuid.UUID) -> bool:
        """Delete role by ID."""
        start_time = time.time()
        try:
            # First delete all user-role assignments
            delete_assignments_stmt = delete(UserRole).where(
                UserRole.role_id == role_id
            )
            await self.session.execute(delete_assignments_stmt)

            # Then delete the role
            delete_role_stmt = delete(Role).where(Role.id == role_id)
            result = await self.session.execute(delete_role_stmt)
            await self.session.commit()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "roles+user_roles", duration_ms)

            success = result.rowcount > 0
            if success:
                logger.info(f"Deleted role {role_id} and its assignments")
            return success
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting role {role_id}: {e}")
            raise

    async def get_user_permissions(self, user_id: uuid.UUID) -> Set[str]:
        """Get all permissions for a user across all their roles."""
        start_time = time.time()
        try:
            stmt = (
                select(User).where(User.id == user_id).options(selectinload(User.roles))
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return set()

            permissions = set()
            if user.roles:
                for role in user.roles:
                    if role.permissions:
                        for permission in role.permissions:
                            permissions.add(permission)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "users_roles_permissions", duration_ms)

            logger.debug(f"User {user_id} has permissions: {permissions}")
            return permissions
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {e}")
            raise

    async def assign_role_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: Optional[uuid.UUID] = None,
    ) -> bool:
        """Assign a role to a user with tenant validation."""
        start_time = time.time()
        try:
            # Get user and role to validate they exist and are in same tenant
            user_stmt = select(User).where(User.id == user_id)
            role_stmt = select(Role).where(Role.id == role_id)

            user_result = await self.session.execute(user_stmt)
            role_result = await self.session.execute(role_stmt)

            user = user_result.scalar_one_or_none()
            role = role_result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found for role assignment")
                return False

            if not role:
                logger.warning(f"Role {role_id} not found for assignment")
                return False

            # Validate same tenant
            if str(user.tenant_id) != str(role.tenant_id):
                logger.warning(
                    f"User {user_id} and role {role_id} are not in the same tenant"
                )
                return False

            # Check if assignment already exists
            existing_stmt = select(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
            existing_result = await self.session.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                logger.info(f"Role {role_id} already assigned to user {user_id}")
                return True

            # Create new assignment
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


async def get_role_repository(session: AsyncSession) -> AsyncRoleRepository:
    """Factory function to create role repository."""
    return AsyncRoleRepository(session)
