import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.cache import core as cache
from backend.app.models import core as models
from backend.app.schemas import core as schemas

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_user_by_email(db: Session, email: str, tenant_id=None):
    q = db.query(models.User).filter(models.User.email == email)
    if tenant_id:
        if isinstance(tenant_id, str):
            try:
                tenant_id = uuid.UUID(tenant_id)
            except ValueError:
                return None
        q = q.filter(models.User.tenant_id == tenant_id)
    return q.first()


def create_user(db: Session, user: schemas.UserCreate):
    # bcrypt has a 72-byte password length limit. Truncate safely at the byte level.
    pw = user.password
    try:
        pw_bytes = pw.encode("utf-8")
    except Exception:
        pw_bytes = str(pw).encode("utf-8")
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
        pw = pw_bytes.decode("utf-8", errors="ignore")

    hashed = pwd_context.hash(pw)
    db_user = models.User(
        email=user.email,
        password_hash=hashed,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        tenant_id=user.tenant_id,
    )
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)

        # Initialize empty cache for new user (tenant-scoped)
        try:
            cache.invalidate_user_cache(str(db_user.tenant_id), str(db_user.id))
        except Exception:
            # best-effort: ignore cache failures
            pass
    except IntegrityError:
        db.rollback()
        raise
    return db_user


def create_tenant(db: Session, tenant: schemas.TenantCreate):
    # if domain provided, return existing tenant to make idempotent in tests/dev
    if tenant.domain:
        existing = (
            db.query(models.Tenant)
            .filter(models.Tenant.domain == tenant.domain)
            .first()
        )
        if existing:
            return existing
    db_t = models.Tenant(name=tenant.name, domain=tenant.domain)
    db.add(db_t)
    try:
        db.commit()
        db.refresh(db_t)
    except IntegrityError:
        db.rollback()
        # try to return existing by domain
        if tenant.domain:
            return (
                db.query(models.Tenant)
                .filter(models.Tenant.domain == tenant.domain)
                .first()
            )
        raise
    return db_t


def create_role(db: Session, role: schemas.RoleCreate):
    db_r = models.Role(
        name=role.name,
        description=role.description or "",
        permissions=role.permissions or [],
        tenant_id=role.tenant_id,
    )
    db.add(db_r)
    # debug
    try:
        print(f"[DEBUG create_role] using bind={getattr(db, 'bind', None)}")
    except Exception:
        pass
    db.commit()
    db.refresh(db_r)

    # Invalidate role-related caches (tenant-scoped)
    try:
        cache.invalidate_role_cache(str(db_r.tenant_id), str(db_r.id))
    except Exception:
        pass
    return db_r


def get_roles_by_tenant(db: Session, tenant_id):
    if isinstance(tenant_id, str):
        try:
            tenant_id = uuid.UUID(tenant_id)
        except Exception:
            pass
    return db.query(models.Role).filter(models.Role.tenant_id == tenant_id).all()


def assign_role_to_user(db: Session, user_id, role_id, assigned_by=None):
    # normalize string UUIDs to uuid.UUID so SQLAlchemy UUID columns accept them
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except Exception:
            pass
    if isinstance(role_id, str):
        try:
            role_id = uuid.UUID(role_id)
        except Exception:
            pass
    if isinstance(assigned_by, str):
        try:
            assigned_by = uuid.UUID(assigned_by)
        except Exception:
            pass

    ur = models.UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
    db.add(ur)
    # debug
    try:
        print(f"[DEBUG assign_role_to_user] using bind={getattr(db, 'bind', None)}")
    except Exception:
        pass
    try:
        db.commit()
        db.refresh(ur)

        # Invalidate user's permission cache (tenant-scoped)
        # need user's tenant id; load user
        try:
            u = db.query(models.User).filter(models.User.id == user_id).first()
            if u is not None:
                cid = getattr(u, "tenant_id", None)
                if cid is not None:
                    cache.invalidate_user_cache(str(cid), str(user_id))
        except Exception:
            pass
    except IntegrityError:
        db.rollback()
        raise
    return ur


def get_user_permissions(db: Session, user_id) -> List[str]:
    from datetime import datetime, timezone

    # normalize user_id strings to UUID for UUID columns
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except Exception:
            pass

    # Check cache first
    # Ensure we include user's tenant when checking cache
    u = db.query(models.User).filter(models.User.id == user_id).first()
    tenant_id_val = None
    if u is not None:
        cid = getattr(u, "tenant_id", None)
        if cid is not None:
            tenant_id_val = str(cid)
    cached_perms = None
    if tenant_id_val is not None:
        cached_perms = cache.get_cached_user_permissions(tenant_id_val, str(user_id))
    if cached_perms is not None:
        return cached_perms

    now = datetime.now(timezone.utc)
    q = (
        db.query(models.Role.permissions)
        .join(models.UserRole, models.UserRole.role_id == models.Role.id)
        .filter(models.UserRole.user_id == user_id)
        .filter(
            (models.UserRole.expires_at.is_(None)) | (models.UserRole.expires_at > now)
        )
    )
    perms = []
    for (p,) in q.all():
        if isinstance(p, list):
            perms.extend(p)
    # deduplicate
    dedup = list(set(perms))

    # Cache the result (tenant-scoped)
    if tenant_id_val is not None:
        try:
            cache.cache_user_permissions(tenant_id_val, str(user_id), dedup)
        except Exception:
            pass
    return dedup


# --- Session / Refresh token helpers ---------------------------------
def _hash_token(token: str) -> str:
    """Return a hex SHA256 of the token for safe storage/comparison."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    db: Session,
    user_id,
    tenant_id,
    access_token: str,
    refresh_token: str,
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Create a Session row storing token and refresh hashes."""
    token_hash = _hash_token(access_token)
    refresh_hash = _hash_token(refresh_token)
    # If a session already exists for this refresh hash, update it to avoid unique constraint errors
    existing = (
        db.query(models.Session)
        .filter(models.Session.refresh_token_hash == refresh_hash)
        .first()
    )

    if existing:
        setattr(existing, "user_id", user_id)
        setattr(existing, "tenant_id", tenant_id)
        setattr(existing, "token_hash", token_hash)
        setattr(existing, "refresh_token_hash", refresh_hash)
        setattr(existing, "ip_address", ip_address)
        setattr(existing, "user_agent", user_agent)
        setattr(existing, "expires_at", expires_at)
        setattr(existing, "last_activity", datetime.now(timezone.utc))
        db.add(existing)
        db.commit()
        db.refresh(existing)
        try:
            cache.invalidate_user_cache(str(tenant_id), str(user_id))
        except Exception:
            pass
        return existing

    s = models.Session(
        user_id=user_id,
        token_hash=token_hash,
        refresh_token_hash=refresh_hash,
        tenant_id=tenant_id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    # invalidate caches for user (session state changed)
    try:
        cache.invalidate_user_cache(str(tenant_id), str(user_id))
    except Exception:
        pass
    return s


def get_session_by_refresh_hash(db: Session, refresh_hash: str):
    """Return a session matching the refresh_token_hash if not expired."""
    now = datetime.now(timezone.utc)
    return (
        db.query(models.Session)
        .filter(
            models.Session.refresh_token_hash == refresh_hash,
            models.Session.expires_at > now,
        )
        .first()
    )


def get_session_by_id(db: Session, session_id):
    # normalize
    if isinstance(session_id, str):
        try:
            session_id = uuid.UUID(session_id)
        except Exception:
            pass
    return db.query(models.Session).filter(models.Session.id == session_id).first()


def get_sessions_by_user(db: Session, user_id):
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except Exception:
            pass
    return db.query(models.Session).filter(models.Session.user_id == user_id).all()


def revoke_all_sessions(db: Session, user_id):
    """Revoke all sessions for a user."""
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except Exception:
            pass
    sessions = db.query(models.Session).filter(models.Session.user_id == user_id).all()
    for s in sessions:
        db.delete(s)
    db.commit()
    try:
        u = db.query(models.User).filter(models.User.id == user_id).first()
        if u is not None:
            cid = getattr(u, "tenant_id", None)
            if cid is not None:
                cache.invalidate_user_cache(str(cid), str(user_id))
    except Exception:
        pass
    return True


def rotate_refresh_token(
    db: Session,
    session_id,
    new_access_token: str,
    new_refresh_token: str,
    new_expires_at: datetime,
):
    """Rotate refresh token for a session: update stored hashes and expiry."""
    s = get_session_by_id(db, session_id)
    if not s:
        return None
    setattr(s, "token_hash", _hash_token(new_access_token))
    setattr(s, "refresh_token_hash", _hash_token(new_refresh_token))
    setattr(s, "expires_at", new_expires_at)
    setattr(s, "last_activity", datetime.now(timezone.utc))
    db.add(s)
    db.commit()
    db.refresh(s)
    try:
        cache.invalidate_user_cache(str(s.tenant_id), str(s.user_id))
    except Exception:
        pass
    return s


def revoke_session(db: Session, session_id):
    """Revoke (delete) a session."""
    s = get_session_by_id(db, session_id)
    if not s:
        return False
    uid = s.user_id
    db.delete(s)
    db.commit()
    try:
        u = db.query(models.User).filter(models.User.id == uid).first()
        if u is not None:
            cid = getattr(u, "tenant_id", None)
            if cid is not None:
                cache.invalidate_user_cache(str(cid), str(uid))
    except Exception:
        pass
    return True


def remove_user_role(db: Session, user_id, role_id):
    """Remove a user role assignment and invalidate cache."""
    # normalize string UUIDs to uuid.UUID
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except Exception:
            pass
    if isinstance(role_id, str):
        try:
            role_id = uuid.UUID(role_id)
        except Exception:
            pass

    ur = (
        db.query(models.UserRole)
        .filter(models.UserRole.user_id == user_id, models.UserRole.role_id == role_id)
        .first()
    )

    if ur:
        db.delete(ur)
        db.commit()
        # Invalidate user's permission cache
        try:
            u = db.query(models.User).filter(models.User.id == user_id).first()
            if u is not None:
                cid = getattr(u, "tenant_id", None)
                if cid is not None:
                    cache.invalidate_user_cache(str(cid), str(user_id))
        except Exception:
            pass
        return True

    return False


def list_users_by_tenant(db: Session, tenant_id):
    if isinstance(tenant_id, str):
        try:
            tenant_id = uuid.UUID(tenant_id)
        except Exception:
            pass
    return db.query(models.User).filter(models.User.tenant_id == tenant_id).all()


def create_audit_log(
    db: Session,
    tenant_id,
    action,
    user_id=None,
    resource_type=None,
    resource_id=None,
    changes=None,
    ip_address=None,
    user_agent=None,
):
    # normalize tenant_id to UUID if provided as string
    if isinstance(tenant_id, str):
        try:
            tenant_id = uuid.UUID(tenant_id)
        except Exception:
            pass
    # normalize user_id/resource_id to UUID if strings
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except Exception:
            pass
    if isinstance(resource_id, str):
        try:
            resource_id = uuid.UUID(resource_id)
        except Exception:
            pass
    al = models.AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(al)
    db.commit()
    db.refresh(al)
    return al


def get_tenant_by_id(db: Session, tenant_id):
    """Return tenant by id (sync helper)"""
    if isinstance(tenant_id, str):
        try:
            tenant_id = uuid.UUID(tenant_id)
        except Exception:
            pass
    return db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
