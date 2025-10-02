"""Async authentication API routes.

This module provides async FastAPI routes for authentication operations,
including login, token refresh, logout, and session management.
"""

import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.core import decode_token
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.db.core import get_async_db
from backend.app.models.core import User
from backend.app.repositories.auth import AsyncAuthRepository, get_auth_repository

logger = get_logger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic models for requests/responses
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    session_id: str


class RefreshRequest(BaseModel):
    refresh_token: str
    tenant_id: Optional[str] = None


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SessionInfo(BaseModel):
    id: str
    tenant_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str
    last_activity: Optional[str]
    expires_at: str


class LogoutResponse(BaseModel):
    message: str
    sessions_revoked: int


def get_client_info(request: Request) -> tuple:
    """Extract client information from request."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.post("/login", response_model=LoginResponse)
async def async_login(
    request: Request,
    login_data: Optional[LoginRequest] = Body(None),
    db: AsyncSession = Depends(get_async_db),
):
    """Authenticate user and create session (async)."""
    try:
        auth_repo = await get_auth_repository(db)

        # Support legacy v1 usage where parameters are passed as query/form params
        if login_data is None:
            # Try query params first
            qp = request.query_params
            email = qp.get("email")
            password = qp.get("password")
            tenant_id_str = qp.get("tenant_id")
            # If not in query, try form body
            if not email or not password:
                try:
                    form = await request.form()
                    email = email or form.get("email")
                    password = password or form.get("password")
                    tenant_id_str = tenant_id_str or form.get("tenant_id")
                except Exception:
                    pass
            # coerce UploadFile values to str when form parsing returns UploadFile
            if isinstance(email, UploadFile):
                email = getattr(email, "filename", None) or str(email)
            if isinstance(password, UploadFile):
                password = getattr(password, "filename", None) or str(password)
            if isinstance(tenant_id_str, UploadFile):
                tenant_id_str = getattr(tenant_id_str, "filename", None) or str(
                    tenant_id_str
                )

            if not email or not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="email and password required",
                )
            tenant_id = uuid.UUID(tenant_id_str) if tenant_id_str else None
        else:
            tenant_id = (
                uuid.UUID(login_data.tenant_id)
                if login_data.tenant_id
                else None
            )
            email = login_data.email
            password = login_data.password

        # Get client info
        ip_address, user_agent = get_client_info(request)

        # Authenticate
        user, session, access_token, refresh_token = await auth_repo.authenticate_user(
            email=email,
            password=password,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not user or not session or not access_token or not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        # Format user response
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "tenant_id": str(user.tenant_id),
            "roles": [role.name for role in user.roles] if user.roles else [],
        }

        # Return JSONResponse and set cookies to be compatible with v1 behavior
        resp = JSONResponse(
            {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_data,
                "session_id": str(session.id),
            }
        )
        # set cookies similar to sync implementation
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
            str(session.id),
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/refresh", response_model=RefreshResponse)
async def async_refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """Refresh access tokens (async)."""
    try:
        auth_repo = await get_auth_repository(db)

        # Read refresh token from cookie to be compatible with v1
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refresh_token cookie required",
            )
        tenant_cookie = request.cookies.get(settings.TENANT_COOKIE_NAME)
        if not tenant_cookie:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tenant_id cookie required",
            )
        try:
            tenant_id = uuid.UUID(tenant_cookie)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant id in cookie",
            )

        # Refresh tokens
        user, session, access_token, refresh_token = await auth_repo.refresh_tokens(
            refresh_token=refresh_token, tenant_id=tenant_id
        )

        if not user or not session or not access_token or not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Return JSONResponse and set cookies to match v1 behavior
        resp = JSONResponse(
            {
                "access_token": access_token,
                "token_type": "bearer",
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
            str(session.id),
            httponly=False,
            secure=False,
            samesite="lax",
            max_age=30 * 24 * 60 * 60,
        )
        resp.set_cookie(
            settings.TENANT_COOKIE_NAME,
            str(session.tenant_id),
            httponly=False,
            secure=settings.TENANT_COOKIE_SECURE,
            samesite="lax",
            max_age=30 * 24 * 60 * 60,
        )
        return resp

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/logout", response_model=LogoutResponse)
async def async_logout(
    session_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Logout single session (async)."""
    try:
        auth_repo = await get_auth_repository(db)

        session_uuid = uuid.UUID(session_id)
        success = await auth_repo.logout_session(session_uuid)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return LogoutResponse(message="Logged out successfully", sessions_revoked=1)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session ID"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.post("/logout-all", response_model=LogoutResponse)
async def async_logout_all(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Logout all sessions for user (async)."""
    try:
        auth_repo = await get_auth_repository(db)

        # If user_id not supplied (v1-style), derive it from Authorization header
        if not user_id:
            auth_header = request.headers.get("authorization") or request.headers.get(
                "Authorization"
            )
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Authorization header",
                )
            try:
                token = auth_header.split()[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        user_uuid = uuid.UUID(user_id)
        revoked_count = await auth_repo.logout_all_sessions(user_uuid)

        return LogoutResponse(
            message=f"Logged out all sessions", sessions_revoked=revoked_count
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )
    except Exception as e:
        logger.error(f"Logout all error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout all failed",
        )


@router.get("/sessions", response_model=List[SessionInfo])
async def async_get_sessions(
    request: Request,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Get all active sessions for user (async)."""
    try:
        auth_repo = await get_auth_repository(db)

        # If no user_id query param provided, derive from Authorization bearer token
        if not user_id:
            auth_header = request.headers.get("authorization") or request.headers.get(
                "Authorization"
            )
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Authorization header",
                )
            try:
                token = auth_header.split()[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )

        user_uuid = uuid.UUID(user_id)
        sessions = await auth_repo.get_user_sessions(user_uuid)

        # Convert to response format
        session_list = []
        for session in sessions:
            session_list.append(
                SessionInfo(
                    id=session["id"],
                    tenant_id=session["tenant_id"],
                    ip_address=session["ip_address"],
                    user_agent=session["user_agent"],
                    created_at=(
                        session["created_at"].isoformat()
                        if session["created_at"]
                        else ""
                    ),
                    last_activity=(
                        session["last_activity"].isoformat()
                        if session["last_activity"]
                        else None
                    ),
                    expires_at=(
                        session["expires_at"].isoformat()
                        if session["expires_at"]
                        else ""
                    ),
                )
            )

        return session_list

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions",
        )
