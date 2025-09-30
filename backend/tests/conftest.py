import os
import sys
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path so `backend` package is importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# Force tests to use a file-backed SQLite DB so both sync and async engines
# created at import-time (in backend.app.db.core) and in-test engines share
# the same database state. We create a temporary .db file and set
# DATABASE_URL before importing the application modules.
tmp_db_path = os.environ.get("TEST_SQLITE_DB_PATH")
if not tmp_db_path:
    tmp_file = tempfile.NamedTemporaryFile(
        prefix="test_db_", suffix=".db", delete=False
    )
    tmp_db_path = tmp_file.name
    tmp_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db_path}"
from backend.main import app

# Ensure module-level settings reflect the test DATABASE_URL so modules that
# import settings at module import-time pick up the test DB URL. This is safe
# because tests set DATABASE_URL before importing application modules above.
try:
    from backend.app.core import config as _config

    _config.reload_settings()
except Exception:
    pass
from backend.app.db.core import Base, get_db

# Clear in-memory rate limiter state between tests to avoid flakiness
from backend.app.middleware.security import clear_in_memory_window_store


@pytest.fixture(autouse=True)
def clear_rate_limit_store_between_tests():
    clear_in_memory_window_store()
    yield
    clear_in_memory_window_store()


@pytest.fixture(scope="session")
def in_memory_engine():
    # Create a file-backed SQLite DB for the whole test session so both sync
    # and async engines (which are created during app import) point to the
    # same file and see the same data.
    database_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(in_memory_engine):
    SessionTesting = sessionmaker(
        bind=in_memory_engine, autoflush=False, autocommit=False
    )
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


@pytest.fixture(scope="session")
def start_fastapi_server():
    """Start a real HTTP server for tests that use `requests`.

    This fixture starts uvicorn in a background thread, picks a free port,
    and sets TEST_BASE_URL env var for tests to use.
    """
    import os
    import socket
    import threading
    import time

    try:
        # `app` is already imported above in this file
        from backend.main import app as fastapi_app
    except Exception as e:
        pytest.skip(f"Could not import backend.main.app: {e}")

    # find a free port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    host, port = s.getsockname()
    s.close()

    try:
        import uvicorn
    except Exception:
        pytest.skip(
            "uvicorn not installed in test environment; cannot start HTTP server"
        )

    config = uvicorn.Config(
        fastapi_app, host="127.0.0.1", port=port, log_level="warning", loop="asyncio"
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    # wait for server to become ready
    import requests

    ready = False
    for _ in range(50):
        try:
            r = requests.get(base_url + "/", timeout=0.5)
            ready = True
            break
        except Exception:
            time.sleep(0.1)

    os.environ["TEST_BASE_URL"] = base_url

    # Ensure settings reflect the runtime test base URL for tools/tests that import settings
    try:
        from backend.app.core import config as _config

        _config.reload_settings()
    except Exception:
        pass

    if not ready:
        pytest.skip(f"FastAPI server did not become ready at {base_url}")

    yield base_url

    # Teardown
    try:
        server.should_exit = True
        thread.join(timeout=5)
    except Exception:
        pass
