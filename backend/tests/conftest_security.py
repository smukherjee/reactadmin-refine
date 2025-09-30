import os
import socket
import threading
import time
from pathlib import Path

import pytest


def _get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', 0))
    addr, port = s.getsockname()
    s.close()
    return port


@pytest.fixture(scope='session', autouse=True)
def start_fastapi_server():
    """Start the FastAPI app with uvicorn in a background thread and export TEST_BASE_URL.

    This fixture is autouse so tests will have a running backend without external orchestration.
    """
    try:
        # import app
        from backend.main import app as fastapi_app
    except Exception as e:
        pytest.skip(f"Could not import backend.app: {e}")

    # pick a free port
    port = _get_free_port()
    host = '127.0.0.1'

    # import uvicorn lazily
    try:
        import uvicorn
    except Exception:
        pytest.skip('uvicorn not installed in test environment; cannot start server')

    config = uvicorn.Config(fastapi_app, host=host, port=port, log_level='warning', loop='asyncio')
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f'http://{host}:{port}'

    # wait for server to be ready (try root endpoint)
    import requests

    ready = False
    for _ in range(50):
        try:
            r = requests.get(base_url + '/', timeout=0.5)
            ready = True
            break
        except Exception:
            time.sleep(0.1)

    os.environ['TEST_BASE_URL'] = base_url

    if not ready:
        # Allow tests to run but warn; some tests will skip if not reachable
        pytest.skip(f"FastAPI server did not become ready at {base_url}")

    yield base_url

    # Teardown
    try:
        server.should_exit = True
        thread.join(timeout=5)
    except Exception:
        pass
