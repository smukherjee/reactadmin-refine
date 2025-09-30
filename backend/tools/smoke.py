"""Quick smoke tests using TestClient to verify key endpoints and auth cookie behavior.

Run this script from the repo root:

    python3 backend/tools/smoke.py

It expects the app to be importable from backend.app.main.core:app. The script
is named so pytest won't accidentally collect it as a test module.
"""

import os
import sys

from fastapi.testclient import TestClient

# Ensure repo root is on path when invoked as a script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.config import settings
from app.main.core import app

client = TestClient(app)


def check(path, method="get", **kwargs):
    fn = getattr(client, method)
    r = fn(path, **kwargs)
    print(f"{method.upper():4} {path} -> {r.status_code}")
    try:
        print(r.json())
    except Exception:
        print(r.text[:400])
    print("-" * 60)
    return r


if __name__ == "__main__":
    print("APP VERSION:", settings.APP_VERSION)

    check("/api/v1/info")
    check("/api/v1/health")
    # cache status endpoint may require no auth for v1
    check("/api/v1/cache/status")
    check("/api/v2/info")

    # Minimal auth smoke: attempt login using credentials from .env or defaults
    user = getattr(settings, "TEST_USER", None)
    pwd = getattr(settings, "TEST_PASS", None)
    if user and pwd:
        print("Attempting login...")
        r = client.post(
            "/api/v1/auth/login",
            data={"username": user, "password": pwd},
        )
        print("Login status:", r.status_code)
        print("Cookies set:", r.cookies.items())
        if r.status_code == 200:
            # try refresh if cookie set
            if "refresh_token" in r.cookies:
                rr = client.post("/api/v1/auth/refresh", cookies=r.cookies)
                print("Refresh status:", rr.status_code)
                print("Refresh cookies:", rr.cookies.items())
    else:
        print("Skipping login smoke: TEST_USER/TEST_PASS not configured in settings")
