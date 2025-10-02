"""Async repository for session operations.

This module provides async database operations for session management,
including authentication, token refresh, and session lifecycle.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.logging import get_logger, log_database_operation
from backend.app.models.core import Session, User

logger = get_logger(__name__)


class AsyncSessionRepository:
    """Async repository for session database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        refresh_token_hash: str,
        tenant_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Session:
        """Create a new user session."""
        start_time = time.time()
        try:
            session = Session(
                user_id=user_id,
                token_hash=token_hash,
                refresh_token_hash=refresh_token_hash,
                tenant_id=tenant_id,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at,
            )

            self.session.add(session)
            await self.session.commit()
            await self.session.refresh(session)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("INSERT", "sessions", duration_ms)

            logger.info(f"Created session {session.id} for user {user_id}")
            return session
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating session: {e}")
            raise

    async def get_by_refresh_hash(self, refresh_hash: str) -> Optional[Session]:
        """Get session by refresh token hash if not expired."""
        start_time = time.time()
        try:
            now = datetime.now(timezone.utc)
            stmt = select(Session).where(
                Session.refresh_token_hash == refresh_hash, Session.expires_at > now
            )
            result = await self.session.execute(stmt)
            session = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "sessions", duration_ms)

            return session
        except Exception as e:
            logger.error(f"Error getting session by refresh hash: {e}")
            raise

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[Session]:
        """Get session by ID."""
        start_time = time.time()
        try:
            stmt = select(Session).where(Session.id == session_id)
            result = await self.session.execute(stmt)
            session = result.scalar_one_or_none()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "sessions", duration_ms)

            return session
        except Exception as e:
            logger.error(f"Error getting session by ID {session_id}: {e}")
            raise

    async def get_sessions_by_user(self, user_id: uuid.UUID) -> List[Session]:
        """Get all active sessions for a user."""
        start_time = time.time()
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                select(Session)
                .where(Session.user_id == user_id, Session.expires_at > now)
                .order_by(Session.created_at.desc())
            )
            result = await self.session.execute(stmt)
            sessions = result.scalars().all()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("SELECT", "sessions", duration_ms, len(sessions))

            return list(sessions)
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            raise

    async def update_refresh_token(
        self,
        session_id: uuid.UUID,
        new_token_hash: str,
        new_refresh_hash: str,
        new_expires_at: datetime,
    ) -> Optional[Session]:
        """Update session with new token hashes (token rotation)."""
        start_time = time.time()
        try:
            stmt = (
                update(Session)
                .where(Session.id == session_id)
                .values(
                    token_hash=new_token_hash,
                    refresh_token_hash=new_refresh_hash,
                    expires_at=new_expires_at,
                    last_activity=datetime.now(timezone.utc),
                )
                .returning(Session)
            )
            result = await self.session.execute(stmt)
            updated_session = result.scalar_one_or_none()

            if updated_session:
                await self.session.commit()
                await self.session.refresh(updated_session)

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("UPDATE", "sessions", duration_ms)

            return updated_session
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating session {session_id}: {e}")
            raise

    async def revoke_session(self, session_id: uuid.UUID) -> bool:
        """Revoke a single session."""
        start_time = time.time()
        try:
            stmt = delete(Session).where(Session.id == session_id)
            result = await self.session.execute(stmt)
            await self.session.commit()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "sessions", duration_ms)

            success = result.rowcount > 0
            if success:
                logger.info(f"Revoked session {session_id}")
            return success
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error revoking session {session_id}: {e}")
            raise

    async def revoke_all_sessions(self, user_id: uuid.UUID) -> int:
        """Revoke all sessions for a user."""
        start_time = time.time()
        try:
            stmt = delete(Session).where(Session.user_id == user_id)
            result = await self.session.execute(stmt)
            await self.session.commit()

            duration_ms = (time.time() - start_time) * 1000
            log_database_operation("DELETE", "sessions", duration_ms)

            revoked_count = result.rowcount
            logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
            return revoked_count
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error revoking all sessions for user {user_id}: {e}")
            raise


async def get_session_repository(session: AsyncSession) -> AsyncSessionRepository:
    """Factory function to create session repository."""
    return AsyncSessionRepository(session)
