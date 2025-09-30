import os
import pytest

try:
    import requests
except Exception:
    requests = None


@pytest.fixture
def url():
    """Return a base URL for performance tests.

    Uses TEST_BASE_URL environment variable if set, otherwise defaults to
    http://127.0.0.1:8001 (the async_perf_test.py default). The fixture will
    skip the test if the server is not reachable to keep runs safe.
    """
    base = os.getenv('TEST_BASE_URL') or 'http://127.0.0.1:8001'
    # quick reachability check
    if requests is None:
        pytest.skip('requests not installed; skipping network perf tests')
    try:
        r = requests.get(base + '/', timeout=1)
        # treat any status code as reachable; non-2xx will still run as test
    except Exception:
        pytest.skip(f"Server not reachable at {base}; skipping perf test")
    return base


@pytest.fixture
async def session():
    """Provide an aiohttp ClientSession for async performance tests.

    The fixture yields a session and ensures it's closed after use.
    """
    try:
        import aiohttp
    except Exception:
        pytest.skip('aiohttp not installed; skipping async perf tests')

    timeout = aiohttp.ClientTimeout(total=30)
    conn = aiohttp.TCPConnector(limit=50)
    session = aiohttp.ClientSession(connector=conn, timeout=timeout)
    try:
        yield session
    finally:
        try:
            await session.close()
        except Exception:
            pass
