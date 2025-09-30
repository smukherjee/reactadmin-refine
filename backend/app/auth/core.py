"""Authentication helpers and dependencies.

This module decodes JWTs, provides a `get_current_user` dependency and
`require_permission` factory. It prefers middleware-injected JWT payloads
when available (attached to `request.state.jwt_payload`).
"""
from __future__ import annotations

import os
from typing import Optional, Dict, Any, TYPE_CHECKING

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from backend.app.db.core import get_db
from backend.app.crud import core as crud
from backend.app.models import core as models

if TYPE_CHECKING:
    # Avoid runtime import cycles for static type checkers
    from backend.app.models.core import User


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def decode_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token and return the payload or raise 401 on error."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _get_payload_from_request(request: Request, token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Prefer middleware-injected payload if present, otherwise decode token."""
    mw_payload = getattr(request.state, "jwt_payload", None)
    if mw_payload:
        return mw_payload
    return decode_token(token)


def get_current_user(request: Request, db: Session = Depends(get_db), payload: Dict[str, Any] = Depends(_get_payload_from_request)) -> "User":
    """Return the current user object based on the token payload.

    Raises 401 if token is invalid or user not found.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    # normalize string UUIDs to uuid.UUID so SQLAlchemy UUID columns accept them
    if isinstance(user_id, str):
        try:
            import uuid

            user_id = uuid.UUID(user_id)
        except Exception:
            pass
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_permission(permission: str):
    """Dependency factory that raises 403 if current user lacks the permission."""

    def _checker(current_user: "User" = Depends(get_current_user), db: Session = Depends(get_db)):
        perms = crud.get_user_permissions(db, current_user.id)
        if permission not in perms:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return True

    return _checker


def tenant_from_request(request: Request) -> Optional[str]:
    """Return client_id from JWT payload attached to request.state if present.

    Returns None if no payload present.
    """
    payload = getattr(request.state, "jwt_payload", None)
    if not payload:
        return None
    return payload.get("client_id")
