import os
import sys
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

# Ensure project root is on sys.path so `backend` package is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.main.core import app
from backend.app.db.core import Base, get_db


@pytest.fixture(scope="session")
def in_memory_engine():
    # create a fresh in-memory SQLite DB for the whole test session
    # Use StaticPool so the same in-memory database is shared across connections/sessions
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(in_memory_engine):
    SessionTesting = sessionmaker(bind=in_memory_engine, autoflush=False, autocommit=False)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function") 
def client(monkeypatch, db_session, in_memory_engine):
    # Clear cache before each test
    from backend.app.cache import core as cache
    cache.clear_all_cache()
    
    # For request handling we create a fresh Session bound to the in-memory engine so
    # each request runs in its own session and sees committed state from test setup.
    from sqlalchemy.orm import sessionmaker

    # For tests we can return the same session object used by the test setup so both
    # test code and request handlers share the same transactional context.
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient

    return TestClient(app)
