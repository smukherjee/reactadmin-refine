from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
from dotenv import load_dotenv
from typing import Generator, AsyncGenerator

load_dotenv()

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

DATABASE_URL = settings.DATABASE_URL

# Sync engine and session (existing)
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Async engine and session (new) - only create if using PostgreSQL
async_engine = None
AsyncSessionLocal = None

if DATABASE_URL.startswith("postgresql://"):
    # Convert sync URL to async URL for PostgreSQL
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
elif DATABASE_URL.startswith("sqlite://"):
    # For SQLite, use aiosqlite driver for async support
    try:
        import aiosqlite
        async_database_url = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        async_engine = create_async_engine(
            async_database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True
        )
        AsyncSessionLocal = async_sessionmaker(
            async_engine, 
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("Async SQLite database engine initialized with aiosqlite")
    except ImportError:
        logger.warning("aiosqlite not available - async operations will not work with SQLite")
        async_engine = None
        AsyncSessionLocal = None

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Async database session not available. PostgreSQL required for async operations.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()