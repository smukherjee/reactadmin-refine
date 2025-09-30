from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.app.core import config as _config
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

# Declarative base (exported)
Base = declarative_base()

# Lazy-initialized engine/session objects
engine = None
SessionLocal = None
async_engine = None
AsyncSessionLocal = None


def _ensure_settings_loaded() -> None:
    """Ensure module-level settings are up-to-date. Safe to call multiple times."""
    try:
        _config.reload_settings()
    except Exception:
        # Best-effort: if reload fails, fall back to whatever settings exist
        pass


def init_sync_engine(database_url: Optional[str] = None):
    """Initialize the synchronous SQLAlchemy engine and sessionmaker if not already set.

    Returns the Engine instance.
    """
    global engine, SessionLocal
    if engine is not None and SessionLocal is not None:
        return engine

    _ensure_settings_loaded()
    from backend.app.core.config import settings

    DATABASE_URL = database_url or settings.DATABASE_URL
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return engine


def init_async_engine(database_url: Optional[str] = None):
    """Initialize the async SQLAlchemy engine and async sessionmaker if supported.

    Returns the async engine or None if async is not available for the configured DB.
    """
    global async_engine, AsyncSessionLocal
    if async_engine is not None and AsyncSessionLocal is not None:
        return async_engine

    _ensure_settings_loaded()
    from backend.app.core.config import settings

    DATABASE_URL = database_url or settings.DATABASE_URL

    if DATABASE_URL.startswith("postgresql://"):
        ASYNC_DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)
        AsyncSessionLocal = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return async_engine
    elif DATABASE_URL.startswith("sqlite://"):
        try:
            import aiosqlite  # noqa: F401

            async_database_url = DATABASE_URL.replace(
                "sqlite://", "sqlite+aiosqlite://"
            )
            async_engine = create_async_engine(
                async_database_url, echo=False, pool_pre_ping=True
            )
            AsyncSessionLocal = async_sessionmaker(
                async_engine, class_=AsyncSession, expire_on_commit=False
            )
            logger.info("Async SQLite database engine initialized with aiosqlite")
            return async_engine
        except ImportError:
            logger.warning(
                "aiosqlite not available - async operations will not work with SQLite"
            )
            async_engine = None
            AsyncSessionLocal = None
            return None


def get_engine():
    """Return the sync engine, initializing it on first access."""
    if engine is None:
        return init_sync_engine()
    return engine


def get_session_factory():
    """Return the sync sessionmaker, initializing engine if needed."""
    if SessionLocal is None:
        init_sync_engine()
    return SessionLocal


def get_async_engine():
    """Return the async engine, initializing if needed. May return None."""
    if async_engine is None:
        return init_async_engine()
    return async_engine


def get_async_session_factory():
    if AsyncSessionLocal is None:
        init_async_engine()
    return AsyncSessionLocal


def get_db() -> Generator:
    Session = get_session_factory()
    if Session is None:
        raise RuntimeError("Synchronous database session factory not initialized")

    db = Session()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency."""
    AsyncSessionFactory = get_async_session_factory()
    if AsyncSessionFactory is None:
        raise RuntimeError(
            "Async database session not available. PostgreSQL or aiosqlite required for async operations."
        )

    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()
