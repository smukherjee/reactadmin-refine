from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.app.cache import core as cache
# auth and crud core modules
from backend.app.auth import core as auth
from backend.app.crud import core as crud
from backend.app.models import core as models
from backend.app.schemas import core as schemas
from backend.app.db.core import engine, Base, get_db
import os
from dotenv import load_dotenv
from datetime import timedelta, datetime, timezone
from jose import jwt
import secrets
from backend.app.crud.core import create_session, get_session_by_refresh_hash, rotate_refresh_token, revoke_session
from backend.app.crud.core import get_sessions_by_user, revoke_all_sessions
from typing import List, Optional, Dict, Any, Union
import uuid
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
# Tenant cookie configuration
TENANT_COOKIE_NAME = os.getenv("TENANT_COOKIE_NAME", "tenant_id")
TENANT_COOKIE_SECURE = os.getenv("TENANT_COOKIE_SECURE", "false").lower() in ("1", "true", "yes")


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: initialize cache and pub/sub listener."""
    client = cache.get_redis_client()
    if client:
        logger.info("Redis cache initialized successfully")
        # start invalidation listener to handle messages from other processes
        def _invalidation_handler(payload: dict):
            try:
                t = payload.get("type")
                if t == "user_permissions_invalidate":
                    uid = payload.get("user_id")
                    cid = payload.get("client_id")
                    if uid and cid:
                        cache.invalidate_user_cache(cid, uid)
                elif t == "role_invalidate":
                    rid = payload.get("role_id")
                    cid = payload.get("client_id")
                    if rid and cid:
                        cache.invalidate_role_cache(cid, rid)
            except Exception:
                logger.exception("Error handling invalidation payload")

        cache.start_invalidation_listener(_invalidation_handler)
    else:
        logger.warning("Redis cache not available - running without cache")

    yield

    # shutdown
    if cache.redis_client:
        try:
            cache.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")


app = FastAPI(title="ReactAdmin-Refine Backend", lifespan=lifespan)

# Attach middleware for tenant extraction and RBAC payload
from backend.app.middleware.core import TenantRBACMiddleware
app.add_middleware(TenantRBACMiddleware)

# create tables if not exist (helpful for initial run)
Base.metadata.create_all(bind=engine)


@app.post("/tenants", response_model=schemas.TenantOut)
def create_tenant(tenant: schemas.TenantCreate, db: Session = Depends(get_db)):
    return crud.create_tenant(db, tenant)


@app.post("/users", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email, client_id=user.client_id)
    if existing:
        # Idempotent: return existing user (useful for tests / retries)
        return existing
    u = crud.create_user(db, user)
    return u


@app.post("/auth/login")
def login(email: str, password: str, client_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email, client_id=client_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    from backend.app.crud.core import pwd_context
    # user.password_hash is a SQLAlchemy Column value at runtime; ensure it's str for verification
    ph = user.password_hash if user.password_hash is None else str(user.password_hash)
    if not pwd_context.verify(password, ph):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    import uuid as _uuid
    to_encode = {"sub": str(user.id), "email": user.email, "client_id": str(user.client_id), "exp": expire, "jti": str(_uuid.uuid4())}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    # create a refresh token (opaque) and persist session
    refresh_token = secrets.token_urlsafe(32)
    # session expiry equals refresh token expiry; set to 30 days
    refresh_expires = datetime.now(timezone.utc) + timedelta(days=30)
    sess = create_session(db, user.id, user.client_id, token, refresh_token, refresh_expires, ip_address=None, user_agent=None)

    # Set refresh token as an HttpOnly secure cookie (TestClient ignores secure flag)
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"access_token": token, "token_type": "bearer", "expires_at": expire.isoformat()})
    resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=False, samesite="lax", max_age=30 * 24 * 60 * 60)
    # Optionally include session id for the client to reference when logging out
    resp.set_cookie("session_id", str(sess.id), httponly=False, secure=False, samesite="lax", max_age=30 * 24 * 60 * 60)
    # Expose tenant id in a non-HttpOnly cookie to allow client to include it on subsequent requests
    resp.set_cookie(TENANT_COOKIE_NAME, str(user.client_id), httponly=False, secure=TENANT_COOKIE_SECURE, samesite="lax", max_age=30 * 24 * 60 * 60)
    return resp



@app.post("/auth/refresh")
def refresh(request: Request, db: Session = Depends(get_db)):
    """Rotate refresh token: verify old refresh token and issue new access + refresh tokens.

    This implements refresh token rotation: the old session is updated with new token hashes.
    """
    from backend.app.crud.core import _hash_token

    # read refresh token from secure HttpOnly cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token cookie required")
    refresh_hash = _hash_token(refresh_token)
    sess = get_session_by_refresh_hash(db, refresh_hash)
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Verify tenant cookie matches session tenant to prevent cross-tenant refresh
    tenant_cookie = request.cookies.get(TENANT_COOKIE_NAME)
    if not tenant_cookie:
        raise HTTPException(status_code=400, detail="tenant_id cookie required")
    if str(sess.client_id) != str(tenant_cookie):
        raise HTTPException(status_code=403, detail="tenant mismatch")

    # Issue new tokens
    import uuid as _uuid
    new_access = jwt.encode({"sub": str(sess.user_id), "client_id": str(sess.client_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "jti": str(_uuid.uuid4())}, SECRET_KEY, algorithm="HS256")
    new_refresh = secrets.token_urlsafe(32)
    new_exp = datetime.now(timezone.utc) + timedelta(days=30)
    rotated = rotate_refresh_token(db, sess.id, new_access, new_refresh, new_exp)
    if not rotated:
        raise HTTPException(status_code=500, detail="Failed to rotate refresh token")
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"access_token": new_access, "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()})
    resp.set_cookie("refresh_token", new_refresh, httponly=True, secure=False, samesite="lax", max_age=30 * 24 * 60 * 60)
    resp.set_cookie("session_id", str(rotated.id), httponly=False, secure=False, samesite="lax", max_age=30 * 24 * 60 * 60)
    resp.set_cookie(TENANT_COOKIE_NAME, str(rotated.client_id), httponly=False, secure=TENANT_COOKIE_SECURE, samesite="lax", max_age=30 * 24 * 60 * 60)
    return resp


@app.post("/auth/logout")
def logout(session_id: str, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    """Logout by revoking the session id. Admins could revoke other sessions.

    For now only a user can revoke their own session.
    """
    # normalize session_id to UUID when possible
    s = None
    sid: Union[str, uuid.UUID]
    try:
        import uuid as _uuid

        sid = _uuid.UUID(session_id)
    except Exception:
        sid = session_id
    s = db.query(models.Session).filter(models.Session.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(s.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot revoke session for another user")
    revoked = revoke_session(db, s.id)
    if not revoked:
        raise HTTPException(status_code=500, detail="Failed to revoke session")
    # Clear cookies
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"message": "Logged out"})
    resp.delete_cookie("refresh_token")
    resp.delete_cookie("session_id")
    resp.delete_cookie(TENANT_COOKIE_NAME)
    return resp



@app.get("/auth/sessions")
def list_sessions(db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    sess = get_sessions_by_user(db, current_user.id)
    out = []
    for s in sess:
        out.append({
            "id": str(s.id),
            "user_id": str(s.user_id),
            "client_id": str(s.client_id),
            "expires_at": getattr(s, 'expires_at').isoformat() if getattr(s, 'expires_at') is not None else None,
            "created_at": getattr(s, 'created_at').isoformat() if getattr(s, 'created_at') is not None else None,
            "last_activity": getattr(s, 'last_activity').isoformat() if getattr(s, 'last_activity') is not None else None,
        })
    return out


@app.post("/auth/logout-all")
def logout_all(db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    revoke_all_sessions(db, current_user.id)
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"message": "All sessions revoked"})
    resp.delete_cookie("refresh_token")
    resp.delete_cookie("session_id")
    resp.delete_cookie(TENANT_COOKIE_NAME)
    return resp



@app.post("/roles", response_model=schemas.RoleOut)
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user), authorized=Depends(auth.require_permission("roles:create"))):
    # only allow creating roles within the same tenant for now
    if role.client_id is None:
        raise HTTPException(status_code=400, detail="client_id required")
    # TODO: check if current_user has permission to create roles; for now only allow same-tenant
    if str(current_user.client_id) != str(role.client_id):
        raise HTTPException(status_code=403, detail="Cannot create role for different tenant")
    return crud.create_role(db, role)


@app.get("/roles", response_model=List[schemas.RoleOut])
def list_roles(client_id: str, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    # tenant-scoped
    if str(current_user.client_id) != str(client_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.get_roles_by_tenant(db, client_id)


@app.post("/users/{user_id}/roles")
def assign_role(user_id: str, role_id: str, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user), authorized=Depends(auth.require_permission("roles:assign"))):
    # only allow assigning roles within same tenant
    return crud.assign_role_to_user(db, user_id, role_id, assigned_by=current_user.id)


# Example protected endpoint that requires a specific permission
@app.get("/protected/resource")
def protected_resource(current_user=Depends(auth.get_current_user), db: Session = Depends(get_db), allowed=Depends(auth.require_permission("read:protected"))):
    return {"status": "ok", "user": str(current_user.id)}


@app.post("/roles/{role_id}/assign-test")
def assign_role_test(role_id: str, user_id: str, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user), authorized=Depends(auth.require_permission("assign:role"))):
    # This endpoint demonstrates an RBAC check before assigning a role
    return crud.assign_role_to_user(db, user_id, role_id, assigned_by=current_user.id)


@app.get("/users", response_model=List[schemas.UserOut])
def list_users(client_id: str, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user), authorized=Depends(auth.require_permission("users:list"))):
    if str(current_user.client_id) != str(client_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.list_users_by_tenant(db, client_id)


@app.post("/audit-logs")
def create_audit(client_id: str, action: str, user_id: Optional[str] = None, resource_type: Optional[str] = None, resource_id: Optional[str] = None, changes: Optional[Dict[str, Any]] = None, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user), authorized=Depends(auth.require_permission("audit:create"))):
    if str(current_user.client_id) != str(client_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.create_audit_log(db, client_id, action, user_id=user_id, resource_type=resource_type, resource_id=resource_id, changes=changes, ip_address=None, user_agent=None)


@app.post("/cache/clear")
def clear_cache(current_user=Depends(auth.get_current_user), authorized=Depends(auth.require_permission("admin:cache"))):
    """Clear all cache entries. Admin only."""
    cache.clear_all_cache()
    return {"message": "Cache cleared successfully"}


@app.get("/cache/status")
def cache_status():
    """Get cache status."""
    return {
        "redis_available": cache.is_redis_available(),
        "redis_url": cache.REDIS_URL.split('@')[-1] if '@' in cache.REDIS_URL else cache.REDIS_URL,  # Hide credentials
        "cache_ttl": cache.CACHE_TTL
    }
