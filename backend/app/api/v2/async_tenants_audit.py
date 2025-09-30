"""Async tenant and audit API routes for v2.

This module provides async FastAPI routes for tenant management and
audit logging operations. It uses async repositories and does not rely on
sync fallbacks (tests should use api/v1 for sync writes or use an async DB).
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.async_auth import (
    get_current_user_async,
    require_permission_async,
    validate_tenant_access_async,
)
from backend.app.core.logging import get_logger
from backend.app.db.core import get_async_db
from backend.app.models.core import Tenant, User
from backend.app.repositories.audit import AsyncAuditRepository, get_audit_repository
from backend.app.repositories.tenants import (
    AsyncTenantRepository,
    get_tenant_repository,
)
from backend.app.schemas.core import TenantCreate, TenantOut

logger = get_logger(__name__)

router = APIRouter(tags=["Tenants & Audit"])


# ================================
# TENANT ENDPOINTS
# ================================


@router.post("/tenants", response_model=TenantOut)
async def async_create_tenant(
    tenant: TenantCreate, db: AsyncSession = Depends(get_async_db)
):
    """Create a new tenant organization (async)."""
    try:
        tenant_repo = await get_tenant_repository(db)

        # Create tenant (with idempotent domain handling)
        new_tenant = await tenant_repo.create(tenant)

        logger.info(
            f"Created/retrieved tenant {new_tenant.id} with name '{new_tenant.name}'"
        )
        return new_tenant

    except Exception as e:
        logger.error(f"Tenant creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant creation failed",
        )


@router.get("/tenants", response_model=List[TenantOut])
async def async_list_tenants(
    skip: int = Query(0, ge=0, description="Number of tenants to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of tenants to return"
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("tenants:list")),
):
    """List all tenant organizations (async) - requires admin permission."""
    try:
        tenant_repo = await get_tenant_repository(db)

        # Get tenants with pagination
        tenants = await tenant_repo.list_all(skip=skip, limit=limit)

        logger.info(
            f"Retrieved {len(tenants)} tenants for admin user {current_user.id}"
        )
        return tenants

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List tenants error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenants",
        )


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
async def async_get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("tenants:read")),
):
    """Get tenant by ID (async)."""
    try:
        tenant_repo = await get_tenant_repository(db)

        # Convert tenant_id to UUID
        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format",
            )

        # Get tenant
        tenant = await tenant_repo.get_by_id(tenant_uuid)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
            )

        return tenant

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tenant error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant",
        )


# ================================
# AUDIT LOG ENDPOINTS
# ================================


@router.post("/audit-logs")
async def async_create_audit_log(
    request: Request,
    action: str,
    client_id: str = Query(..., description="Tenant/Client ID"),
    user_id: Optional[str] = Query(
        None, description="User ID who performed the action"
    ),
    resource_type: Optional[str] = Query(None, description="Type of resource affected"),
    resource_id: Optional[str] = Query(None, description="ID of resource affected"),
    changes_json: Optional[str] = Query(
        None, description="JSON string of changes made"
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("audit:create")),
):
    """Create a new audit log entry (async)."""
    try:
        # Validate client_id format first so invalid IDs return 400 before tenant access checks
        try:
            client_uuid = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format"
            )

        # Validate tenant access
        validate_tenant_access_async(current_user, client_id)

        audit_repo = await get_audit_repository(db)

        # Convert optional UUIDs
        try:
            user_uuid = uuid.UUID(user_id) if user_id else None
            resource_uuid = uuid.UUID(resource_id) if resource_id else None
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format"
            )

        # Parse changes JSON if provided
        changes = None
        if changes_json:
            try:
                changes = json.loads(changes_json)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON format for changes",
                )

        # Extract client info from request
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Create audit log
        audit_log = await audit_repo.create(
            client_id=client_uuid,
            action=action,
            user_id=user_uuid,
            resource_type=resource_type,
            resource_id=resource_uuid,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(
            f"Created audit log {audit_log.id} for action '{action}' by user {current_user.id}"
        )

        return {
            "id": str(audit_log.id),
            "client_id": str(audit_log.client_id),
            "action": audit_log.action,
            "user_id": (
                str(audit_log.user_id) if audit_log.user_id is not None else None
            ),
            "resource_type": audit_log.resource_type,
            "resource_id": (
                str(audit_log.resource_id)
                if audit_log.resource_id is not None
                else None
            ),
            "created_at": audit_log.created_at,
            "ip_address": audit_log.ip_address,
            "user_agent": audit_log.user_agent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit log creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audit log creation failed",
        )


@router.get("/audit-logs")
async def async_list_audit_logs(
    client_id: str = Query(..., description="Tenant/Client ID to filter audit logs"),
    skip: int = Query(0, ge=0, description="Number of audit logs to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of audit logs to return"
    ),
    action: Optional[str] = Query(None, description="Filter by action"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("audit:read")),
):
    """List audit logs by tenant with filtering (async)."""
    try:
        # Validate tenant access
        validate_tenant_access_async(current_user, client_id)

        audit_repo = await get_audit_repository(db)

        # Convert string UUIDs
        try:
            client_uuid = uuid.UUID(client_id)
            user_uuid = uuid.UUID(user_id) if user_id else None
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format"
            )

        # Get audit logs with filtering
        audit_logs = await audit_repo.list_by_tenant(
            client_id=client_uuid,
            skip=skip,
            limit=limit,
            action=action,
            user_id=user_uuid,
            resource_type=resource_type,
        )

        # Format response
        result = []
        for log in audit_logs:
            result.append(
                {
                    "id": str(log.id),
                    "client_id": str(log.client_id),
                    "action": log.action,
                    "user_id": str(log.user_id) if log.user_id is not None else None,
                    "resource_type": log.resource_type,
                    "resource_id": (
                        str(log.resource_id) if log.resource_id is not None else None
                    ),
                    "changes": log.changes,
                    "created_at": log.created_at,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                }
            )

        logger.info(f"Retrieved {len(audit_logs)} audit logs for tenant {client_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List audit logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs",
        )


@router.get("/audit-logs/statistics")
async def async_get_audit_statistics(
    client_id: str = Query(..., description="Tenant/Client ID for statistics"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("audit:read")),
):
    """Get audit log statistics for a tenant (async)."""
    try:
        # Validate tenant access
        validate_tenant_access_async(current_user, client_id)

        audit_repo = await get_audit_repository(db)

        # Convert client_id to UUID
        try:
            client_uuid = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid client_id format",
            )

        # Get statistics
        stats = await audit_repo.get_statistics(client_uuid)

        logger.info(f"Retrieved audit statistics for tenant {client_id}")
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit statistics",
        )


@router.delete("/audit-logs/cleanup")
async def async_cleanup_old_audit_logs(
    days_to_keep: int = Query(
        90, ge=1, le=365, description="Number of days of audit logs to keep"
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_async),
    authorized: bool = Depends(require_permission_async("audit:admin")),
):
    """Delete old audit logs (admin only) (async)."""
    try:
        audit_repo = await get_audit_repository(db)

        # Delete old logs
        deleted_count = await audit_repo.delete_old_logs(days_to_keep)

        logger.info(
            f"Admin {current_user.id} cleaned up {deleted_count} old audit logs"
        )

        return {
            "message": f"Successfully deleted {deleted_count} audit logs older than {days_to_keep} days",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audit log cleanup failed",
        )


# The v2 module above contains the canonical async implementations. The
# previous additional handlers below were duplicates/legacy and performed
# sync fallbacks using run_in_threadpool which defeats the purpose of v2.
# Keep this module pure async: tests should call /api/v1 for sync write
# compatibility or configure an async-capable test DB.
