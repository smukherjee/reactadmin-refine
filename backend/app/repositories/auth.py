"""Async repository for authentication operations.

This module provides async database operations for authentication,
including credential verification, token management, and account security.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import get_logger, log_database_operation
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from backend.app.models.core import Session, User
from backend.app.repositories.sessions import AsyncSessionRepository

logger = get_logger(__name__)


class AsyncAuthRepository:
    """Async repository for authentication database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = AsyncSessionRepository(session)

    async def authenticate_user(
        self,
        email: str,
        password: str,
        client_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[Session], Optional[str], Optional[str]]:
        """
        Authenticate user credentials and create session.

        Returns:
            Tuple of (user, session, access_token, refresh_token) or (None, None, None, None)
        """
        start_time = time.time()
        try:
            # Get user with relationships loaded
            stmt = (
                select(User)
                .where(User.email == email, User.is_active == True)
                .options(selectinload(User.tenant), selectinload(User.roles))
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                duration_ms = (time.time() - start_time) * 1000
                log_database_operation("SELECT", "users", duration_ms)
                logger.warning(f"Failed authentication attempt for email: {email}")
                return None, None, None, None

            stored_hash = getattr(user, "password_hash", None)
            if not isinstance(stored_hash, str) or not verify_password(
                password, stored_hash
            ):
                duration_ms = (time.time() - start_time) * 1000
                log_database_operation("SELECT", "users", duration_ms)
                logger.warning(f"Failed authentication attempt for email: {email}")
                return None, None, None, None

            # Update last login
            user_id = uuid.UUID(str(user.id))
            await self._update_last_login(user_id)

            # Create tokens
            access_token = create_access_token(
                {"sub": str(user.id), "client_id": str(client_id)}
            )
            refresh_token = create_refresh_token(
                {"sub": str(user.id), "client_id": str(client_id)}
            )

            # Create session
            session = await self.session_repo.create_session(
                user_id=user_id,
                token_hash=self._hash_token(access_token),
                refresh_token_hash=self._hash_token(refresh_token),
                client_id=client_id,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + 24 * 60 * 60,  # 24 hours
                    tz=timezone.utc,
                ),
            )

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT+INSERT", "users+sessions", duration_ms)

            logger.info(f"Successful authentication for user {user.id}")
            return user, session, access_token, refresh_token

        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            raise

    async def refresh_tokens(
        self, refresh_token: str, client_id: uuid.UUID
    ) -> Tuple[Optional[User], Optional[Session], Optional[str], Optional[str]]:
        """
        Refresh access tokens using refresh token.

        Returns:
            Tuple of (user, session, new_access_token, new_refresh_token) or (None, None, None, None)
        """
        start_time = time.time()
        try:
            refresh_hash = self._hash_token(refresh_token)

            # Get session by refresh token hash
            session = await self.session_repo.get_by_refresh_hash(refresh_hash)
            if not session or str(session.client_id) != str(client_id):
                logger.warning(f"Invalid refresh token attempt for client {client_id}")
                return None, None, None, None

            # Get user with relationships
            user_id = uuid.UUID(str(session.user_id))
            stmt = (
                select(User)
                .where(User.id == user_id, User.is_active == True)
                .options(selectinload(User.tenant), selectinload(User.roles))
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User {user_id} not found or inactive")
                return None, None, None, None

            # Create new tokens
            new_access_token = create_access_token(
                {"sub": str(user.id), "client_id": str(client_id)}
            )
            new_refresh_token = create_refresh_token(
                {"sub": str(user.id), "client_id": str(client_id)}
            )

            # Update session with new tokens (token rotation)
            session_id = uuid.UUID(str(session.id))
            updated_session = await self.session_repo.update_refresh_token(
                session_id=session_id,
                new_token_hash=self._hash_token(new_access_token),
                new_refresh_hash=self._hash_token(new_refresh_token),
                new_expires_at=datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + 24 * 60 * 60,  # 24 hours
                    tz=timezone.utc,
                ),
            )

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT+UPDATE", "users+sessions", duration_ms)

            logger.info(f"Successful token refresh for user {user.id}")
            return user, updated_session, new_access_token, new_refresh_token

        except Exception as e:
            logger.error(f"Error during token refresh: {e}")
            raise

    async def logout_session(self, session_id: uuid.UUID) -> bool:
        """Logout a single session."""
        start_time = time.time()
        try:
            success = await self.session_repo.revoke_session(session_id)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "sessions", duration_ms)

            if success:
                logger.info(f"Logged out session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            raise

    async def logout_all_sessions(self, user_id: uuid.UUID) -> int:
        """Logout all sessions for a user."""
        start_time = time.time()
        try:
            revoked_count = await self.session_repo.revoke_all_sessions(user_id)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "sessions", duration_ms)

            logger.info(f"Logged out all sessions for user {user_id}")
            return revoked_count
        except Exception as e:
            logger.error(f"Error during logout all: {e}")
            raise

    async def get_user_sessions(self, user_id: uuid.UUID) -> list:
        """Get all active sessions for a user."""
        start_time = time.time()
        try:
            sessions = await self.session_repo.get_sessions_by_user(user_id)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "sessions", duration_ms, len(sessions))

            # Format sessions for API response
            session_list = []
            for session in sessions:
                session_list.append(
                    {
                        "id": str(session.id),
                        "client_id": str(session.client_id),
                        "ip_address": session.ip_address,
                        "user_agent": session.user_agent,
                        "created_at": session.created_at,
                        "last_activity": session.last_activity,
                        "expires_at": session.expires_at,
                    }
                )

            return session_list
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            raise

    async def _update_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp."""
        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(last_login=datetime.now(timezone.utc))
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            # Don't raise - this is not critical

    def _hash_token(self, token: str) -> str:
        """Hash token for storage (simple hash for now)."""
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()


async def get_auth_repository(session: AsyncSession) -> AsyncAuthRepository:
    """Factory function to create auth repository."""
    return AsyncAuthRepository(session)
