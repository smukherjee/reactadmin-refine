"""Async repository for tenant operations.

This module provides async database operations for tenant management,
including tenant creation and organization management.
"""

import time
import uuid
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger, log_database_operation
from backend.app.models.core import Tenant
from backend.app.schemas.core import TenantCreate

logger = get_logger(__name__)


class AsyncTenantRepository:
    """Async repository for tenant database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        start_time = time.time()
        try:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            result = await self.session.execute(stmt)
            tenant = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "tenants", duration_ms)

            return tenant
        except Exception as e:
            logger.error(f"Error getting tenant by ID {tenant_id}: {e}")
            raise

    async def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get tenant by domain."""
        start_time = time.time()
        try:
            stmt = select(Tenant).where(Tenant.domain == domain)
            result = await self.session.execute(stmt)
            tenant = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "tenants", duration_ms)

            return tenant
        except Exception as e:
            logger.error(f"Error getting tenant by domain {domain}: {e}")
            raise

    async def create(self, tenant_data: TenantCreate) -> Tenant:
        """Create a new tenant with idempotent domain handling."""
        start_time = time.time()
        try:
            # Check if tenant with domain already exists (idempotent)
            if tenant_data.domain:
                existing = await self.get_by_domain(tenant_data.domain)
                if existing:
                    logger.info(
                        f"Tenant with domain {tenant_data.domain} already exists, returning existing"
                    )
                    return existing

            # Create new tenant
            tenant = Tenant(name=tenant_data.name, domain=tenant_data.domain)

            self.session.add(tenant)
            await self.session.commit()
            await self.session.refresh(tenant)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("INSERT", "tenants", duration_ms)

            logger.info(f"Created tenant {tenant.id} with name '{tenant.name}'")
            return tenant

        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(
                f"Integrity error creating tenant, checking for existing: {e}"
            )

            # Try to return existing by domain on integrity error
            if tenant_data.domain:
                existing = await self.get_by_domain(tenant_data.domain)
                if existing:
                    return existing
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating tenant: {e}")
            raise

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """List all tenants with pagination."""
        start_time = time.time()
        try:
            stmt = (
                select(Tenant)
                .offset(skip)
                .limit(limit)
                .order_by(Tenant.created_at.desc())
            )
            result = await self.session.execute(stmt)
            tenants = result.scalars().all()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "tenants", duration_ms, len(tenants))

            return list(tenants)
        except Exception as e:
            logger.error(f"Error listing tenants: {e}")
            raise

    async def update(self, tenant_id: uuid.UUID, updates: dict) -> Optional[Tenant]:
        """Update tenant by ID."""
        start_time = time.time()
        try:
            stmt = (
                update(Tenant)
                .where(Tenant.id == tenant_id)
                .values(**updates)
                .returning(Tenant)
            )
            result = await self.session.execute(stmt)
            updated_tenant = result.scalar_one_or_none()

            if updated_tenant:
                await self.session.commit()
                await self.session.refresh(updated_tenant)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("UPDATE", "tenants", duration_ms)

            return updated_tenant
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating tenant {tenant_id}: {e}")
            raise

    async def delete(self, tenant_id: uuid.UUID) -> bool:
        """Delete tenant by ID."""
        start_time = time.time()
        try:
            stmt = delete(Tenant).where(Tenant.id == tenant_id)
            result = await self.session.execute(stmt)
            await self.session.commit()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "tenants", duration_ms)

            success = result.rowcount > 0
            if success:
                logger.info(f"Deleted tenant {tenant_id}")
            return success
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting tenant {tenant_id}: {e}")
            raise


async def get_tenant_repository(session: AsyncSession) -> AsyncTenantRepository:
    """Factory function to create tenant repository."""
    return AsyncTenantRepository(session)
