"""Async repository for audit log operations.

This module provides async database operations for audit logging,
including creating audit trails for security and compliance.
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import get_logger, log_database_operation
from backend.app.models.core import AuditLog

logger = get_logger(__name__)


class AsyncAuditRepository:
    """Async repository for audit log database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        tenant_id: uuid.UUID,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create a new audit log entry."""
        start_time = time.time()
        try:
            audit_log = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                changes=changes or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self.session.add(audit_log)
            await self.session.commit()
            await self.session.refresh(audit_log)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("INSERT", "audit_logs", duration_ms)

            logger.info(
                f"Created audit log {audit_log.id} for action '{action}' by user {user_id}"
            )
            return audit_log

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating audit log: {e}")
            raise

    async def get_by_id(self, audit_id: uuid.UUID) -> Optional[AuditLog]:
        """Get audit log by ID."""
        start_time = time.time()
        try:
            stmt = select(AuditLog).where(AuditLog.id == audit_id)
            result = await self.session.execute(stmt)
            audit_log = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "audit_logs", duration_ms)

            return audit_log
        except Exception as e:
            logger.error(f"Error getting audit log by ID {audit_id}: {e}")
            raise

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        action: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
    ) -> List[AuditLog]:
        """List audit logs by tenant with optional filtering."""
        start_time = time.time()
        try:
            stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

            # Apply filters
            if action:
                stmt = stmt.where(AuditLog.action == action)
            if user_id:
                stmt = stmt.where(AuditLog.user_id == user_id)
            if resource_type:
                stmt = stmt.where(AuditLog.resource_type == resource_type)

            # Add pagination and ordering
            stmt = stmt.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())

            result = await self.session.execute(stmt)
            audit_logs = result.scalars().all()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "audit_logs", duration_ms, len(audit_logs))

            return list(audit_logs)
        except Exception as e:
            logger.error(f"Error listing audit logs for tenant {tenant_id}: {e}")
            raise

    async def list_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        """List audit logs by user."""
        start_time = time.time()
        try:
            stmt = (
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .offset(skip)
                .limit(limit)
                .order_by(AuditLog.created_at.desc())
            )
            result = await self.session.execute(stmt)
            audit_logs = result.scalars().all()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "audit_logs", duration_ms, len(audit_logs))

            return list(audit_logs)
        except Exception as e:
            logger.error(f"Error listing audit logs for user {user_id}: {e}")
            raise

    async def delete_old_logs(self, days_to_keep: int = 90) -> int:
        """Delete audit logs older than specified days."""
        from datetime import datetime, timedelta, timezone

        start_time = time.time()
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            stmt = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
            result = await self.session.execute(stmt)
            await self.session.commit()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "audit_logs", duration_ms)

            deleted_count = result.rowcount
            logger.info(
                f"Deleted {deleted_count} audit logs older than {days_to_keep} days"
            )
            return deleted_count
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting old audit logs: {e}")
            raise

    async def get_statistics(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        """Get audit log statistics for a tenant."""
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import func, text

        start_time = time.time()
        try:
            # Total count
            total_stmt = select(func.count(AuditLog.id)).where(
                AuditLog.tenant_id == tenant_id
            )
            total_result = await self.session.execute(total_stmt)
            total_count = total_result.scalar()

            # Count by action
            action_stmt = (
                select(AuditLog.action, func.count(AuditLog.id))
                .where(AuditLog.tenant_id == tenant_id)
                .group_by(AuditLog.action)
                .limit(10)
            )
            action_result = await self.session.execute(action_stmt)
            action_rows = action_result.fetchall()
            action_counts = {row[0]: row[1] for row in action_rows}

            # Recent activity (last 24 hours)
            yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_stmt = select(func.count(AuditLog.id)).where(
                AuditLog.tenant_id == tenant_id, AuditLog.created_at > yesterday
            )
            recent_result = await self.session.execute(recent_stmt)
            recent_count = recent_result.scalar()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "audit_logs_stats", duration_ms)

            # Include both a top_actions summary and a direct actions map for compatibility
            return {
                "total_logs": total_count,
                "recent_logs_24h": recent_count,
                "top_actions": action_counts,
                "actions": action_counts,
            }
        except Exception as e:
            logger.error(f"Error getting audit statistics for tenant {tenant_id}: {e}")
            raise


async def get_audit_repository(session: AsyncSession) -> AsyncAuditRepository:
    """Factory function to create audit repository."""
    return AsyncAuditRepository(session)
