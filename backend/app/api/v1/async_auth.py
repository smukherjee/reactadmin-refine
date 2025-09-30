"""Async authentication API routes.

This module provides async FastAPI routes for authentication operations,
including login, token refresh, logout, and session management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid

from backend.app.db.core import get_async_db
from backend.app.repositories.auth import get_auth_repository, AsyncAuthRepository
from backend.app.core.logging import get_logger
from backend.app.models.core import User

logger = get_logger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic models for requests/responses
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    client_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    session_id: str


class RefreshRequest(BaseModel):
    refresh_token: str
    client_id: Optional[str] = None


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SessionInfo(BaseModel):
    id: str
    client_id: str
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
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """Authenticate user and create session (async)."""
    try:
        auth_repo = await get_auth_repository(db)
        
        # Generate client ID if not provided
        client_id = uuid.uuid4() if not login_data.client_id else uuid.UUID(login_data.client_id)
        
        # Get client info
        ip_address, user_agent = get_client_info(request)
        
        # Authenticate
        user, session, access_token, refresh_token = await auth_repo.authenticate_user(
            email=login_data.email,
            password=login_data.password,
            client_id=client_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not user or not session or not access_token or not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Format user response
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "tenant_id": str(user.client_id),
            "roles": [role.name for role in user.roles] if user.roles else []
        }
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_data,
            session_id=str(session.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/refresh", response_model=RefreshResponse)
async def async_refresh_token(
    refresh_data: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """Refresh access tokens (async)."""
    try:
        auth_repo = await get_auth_repository(db)
        
        # Generate client ID if not provided
        client_id = uuid.uuid4() if not refresh_data.client_id else uuid.UUID(refresh_data.client_id)
        
        # Refresh tokens
        user, session, access_token, refresh_token = await auth_repo.refresh_tokens(
            refresh_token=refresh_data.refresh_token,
            client_id=client_id
        )
        
        if not user or not session or not access_token or not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return RefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return LogoutResponse(
            message="Logged out successfully",
            sessions_revoked=1
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all", response_model=LogoutResponse)
async def async_logout_all(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Logout all sessions for user (async)."""
    try:
        auth_repo = await get_auth_repository(db)
        
        user_uuid = uuid.UUID(user_id)
        revoked_count = await auth_repo.logout_all_sessions(user_uuid)
        
        return LogoutResponse(
            message=f"Logged out all sessions",
            sessions_revoked=revoked_count
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )
    except Exception as e:
        logger.error(f"Logout all error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout all failed"
        )


@router.get("/sessions", response_model=List[SessionInfo])
async def async_get_sessions(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Get all active sessions for user (async)."""
    try:
        auth_repo = await get_auth_repository(db)
        
        user_uuid = uuid.UUID(user_id)
        sessions = await auth_repo.get_user_sessions(user_uuid)
        
        # Convert to response format
        session_list = []
        for session in sessions:
            session_list.append(SessionInfo(
                id=session["id"],
                client_id=session["client_id"],
                ip_address=session["ip_address"],
                user_agent=session["user_agent"],
                created_at=session["created_at"].isoformat() if session["created_at"] else "",
                last_activity=session["last_activity"].isoformat() if session["last_activity"] else None,
                expires_at=session["expires_at"].isoformat() if session["expires_at"] else ""
            ))
        
        return session_list
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )