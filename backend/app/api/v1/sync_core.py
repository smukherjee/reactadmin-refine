import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.auth import core as auth
from backend.app.cache import core as cache
from backend.app.core.config import settings
from backend.app.crud import core as crud
from backend.app.db.core import get_db
from backend.app.models import core as models
from backend.app.schemas import core as schemas

router = APIRouter()


@router.post("/tenants", response_model=schemas.TenantOut)
def create_tenant(tenant: schemas.TenantCreate, db: Session = Depends(get_db)):
    return crud.create_tenant(db, tenant)


@router.post("/users", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email, tenant_id=user.tenant_id)
    if existing:
        return existing
    u = crud.create_user(db, user)
    return u


@router.post("/auth/login")
def login(email: str, password: str, tenant_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email, tenant_id=tenant_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    from backend.app.crud.core import pwd_context

    ph = user.password_hash if user.password_hash is None else str(user.password_hash)
    if not pwd_context.verify(password, ph):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    import uuid as _uuid

    to_encode = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "exp": expire,
        "jti": str(_uuid.uuid4()),
    }
    from jose import jwt

    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    refresh_token = secrets.token_urlsafe(32)
    refresh_expires = datetime.now(timezone.utc) + timedelta(days=30)
    sess = crud.create_session(
        db,
        user.id,
        user.tenant_id,
        token,
        refresh_token,
        refresh_expires,
        ip_address=None,
        user_agent=None,
    )
    from fastapi.responses import JSONResponse

    resp = JSONResponse(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expire.isoformat(),
        }
    )
    resp.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    resp.set_cookie(
        "session_id",
        str(sess.id),
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    resp.set_cookie(
        settings.TENANT_COOKIE_NAME,
        str(user.tenant_id),
        httponly=False,
        secure=settings.TENANT_COOKIE_SECURE,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    return resp


@router.post("/auth/refresh")
def refresh(request: Request, db: Session = Depends(get_db)):
    from backend.app.crud.core import (
        _hash_token,
        get_session_by_refresh_hash,
        rotate_refresh_token,
    )

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token cookie required")
    refresh_hash = _hash_token(refresh_token)
    sess = get_session_by_refresh_hash(db, refresh_hash)
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    tenant_cookie = request.cookies.get(settings.TENANT_COOKIE_NAME)
    if not tenant_cookie:
        raise HTTPException(status_code=400, detail="tenant_id cookie required")
    if str(sess.tenant_id) != str(tenant_cookie):
        raise HTTPException(status_code=403, detail="tenant mismatch")
    import uuid as _uuid

    from jose import jwt

    new_access = jwt.encode(
        {
            "sub": str(sess.user_id),
            "tenant_id": str(sess.tenant_id),
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "jti": str(_uuid.uuid4()),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    new_refresh = secrets.token_urlsafe(32)
    new_exp = datetime.now(timezone.utc) + timedelta(days=30)
    rotated = rotate_refresh_token(db, sess.id, new_access, new_refresh, new_exp)
    if not rotated:
        raise HTTPException(status_code=500, detail="Failed to rotate refresh token")
    from fastapi.responses import JSONResponse

    resp = JSONResponse(
        {
            "access_token": new_access,
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            ).isoformat(),
        }
    )
    resp.set_cookie(
        "refresh_token",
        new_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    resp.set_cookie(
        "session_id",
        str(rotated.id),
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    resp.set_cookie(
        settings.TENANT_COOKIE_NAME,
        str(rotated.tenant_id),
        httponly=False,
        secure=settings.TENANT_COOKIE_SECURE,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    return resp


@router.post("/auth/logout")
def logout(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session ID") from exc

    s = db.query(models.Session).filter(models.Session.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(s.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Cannot revoke session for another user"
        )
    revoked = crud.revoke_session(db, s.id)
    if not revoked:
        raise HTTPException(status_code=500, detail="Failed to revoke session")
    from fastapi.responses import JSONResponse

    resp = JSONResponse({"message": "Logged out"})
    resp.delete_cookie("refresh_token")
    resp.delete_cookie("session_id")
    resp.delete_cookie(settings.TENANT_COOKIE_NAME)
    return resp


@router.get("/auth/sessions")
def list_sessions(
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    sess = crud.get_sessions_by_user(db, current_user.id)
    out = []
    for s in sess:
        out.append(
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "tenant_id": str(s.tenant_id),
                "expires_at": (
                    getattr(s, "expires_at").isoformat()
                    if getattr(s, "expires_at") is not None
                    else None
                ),
                "created_at": (
                    getattr(s, "created_at").isoformat()
                    if getattr(s, "created_at") is not None
                    else None
                ),
                "last_activity": (
                    getattr(s, "last_activity").isoformat()
                    if getattr(s, "last_activity") is not None
                    else None
                ),
            }
        )
    return out


@router.post("/auth/logout-all")
def logout_all(
    db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)
):
    crud.revoke_all_sessions(db, current_user.id)
    from fastapi.responses import JSONResponse

    resp = JSONResponse({"message": "All sessions revoked"})
    resp.delete_cookie("refresh_token")
    resp.delete_cookie("session_id")
    resp.delete_cookie(settings.TENANT_COOKIE_NAME)
    return resp


@router.post("/roles", response_model=schemas.RoleOut)
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db)):
    if role.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant_id required")
    return crud.create_role(db, role)


@router.get("/roles", response_model=List[schemas.RoleOut])
def list_roles(tenant_id: str, db: Session = Depends(get_db)):
    return crud.get_roles_by_tenant(db, tenant_id)


@router.post("/users/{user_id}/roles")
def assign_role(user_id: str, payload: dict, db: Session = Depends(get_db)):
    role_id = payload.get("role_id") or payload.get("roleId") or payload.get("role_id")
    if not role_id:
        raise HTTPException(status_code=400, detail="role_id required in body")
    return crud.assign_role_to_user(db, user_id, role_id, assigned_by=None)


@router.get("/protected/resource")
def protected_resource(
    current_user=Depends(auth.get_current_user),
    db: Session = Depends(get_db),
    allowed=Depends(auth.require_permission("read:protected")),
):
    return {"status": "ok", "user": str(current_user.id)}


@router.post("/roles/{role_id}/assign-test")
def assign_role_test(
    role_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
    authorized=Depends(auth.require_permission("assign:role")),
):
    return crud.assign_role_to_user(db, user_id, role_id, assigned_by=current_user.id)


@router.get("/users", response_model=List[schemas.UserOut])
def list_users(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
    authorized=Depends(auth.require_permission("users:list")),
):
    if str(current_user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.list_users_by_tenant(db, tenant_id)


@router.post("/audit-logs")
def create_audit(
    tenant_id: str,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
    authorized=Depends(auth.require_permission("audit:create")),
):
    if str(current_user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.create_audit_log(
        db,
        tenant_id,
        action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=None,
        user_agent=None,
    )


@router.post("/cache/clear")
def clear_cache(
    current_user=Depends(auth.get_current_user),
    authorized=Depends(auth.require_permission("admin:cache")),
):
    cache.clear_all_cache()
    return {"message": "Cache cleared successfully"}


@router.get("/cache/status")
def cache_status():
    return {
        "redis_available": cache.is_redis_available(),
        "redis_url": (
            cache.REDIS_URL.split("@")[-1]
            if "@" in cache.REDIS_URL
            else cache.REDIS_URL
        ),
        "cache_ttl": cache.CACHE_TTL,
    }


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/detailed")
def detailed_health_check(db: Session = Depends(get_db)):
    """Legacy sync v1 detailed health endpoint - delegates to shared service."""
    from backend.app.services.health import collect_detailed_health

    overall_status, components, timings = collect_detailed_health(db)

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "components": components,
    }


@router.get("/metrics")
def metrics():
    """System metrics endpoint (sync v1) returning cached metrics and uptime."""
    try:
        from backend.app.services.system_metrics import get_cached_system_metrics

        metrics = get_cached_system_metrics()

        # Calculate approximate uptime from process create_time if possible
        try:
            import os
            import time

            import psutil

            process = psutil.Process(os.getpid())
            uptime_seconds = time.time() - process.create_time()
            metrics["uptime_seconds"] = round(uptime_seconds, 2)
        except Exception:
            metrics.setdefault("uptime_seconds", 0.0)

        # Ensure required keys exist for tests
        metrics.setdefault("cpu_percent", 0.0)
        metrics.setdefault("memory_percent", 0.0)
        metrics.setdefault("memory_available_mb", 0.0)
        metrics.setdefault("disk_usage_percent", 0.0)

        return metrics
    except Exception as e:
        # Fallback: return minimal metrics using psutil if available
        try:
            import os
            import time

            import psutil

            process = psutil.Process(os.getpid())
            uptime_seconds = time.time() - process.create_time()
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_available_mb": round(
                    psutil.virtual_memory().available / 1024 / 1024, 2
                ),
                "disk_usage_percent": psutil.disk_usage("/").percent,
                "uptime_seconds": round(uptime_seconds, 2),
            }
        except Exception:
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_available_mb": 0.0,
                "disk_usage_percent": 0.0,
                "uptime_seconds": 0.0,
                "error": str(e),
            }


@router.get("/readiness")
def readiness_check(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        # Use centralized safe_redis_call to avoid blocking on redis
        ping_resp = cache.safe_redis_call(lambda c: c.ping(), timeout=0.25)
        if not ping_resp.get("ok"):
            raise Exception(f"redis ping failed: {ping_resp.get('error')}")
        return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/liveness")
def liveness_check():
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}
