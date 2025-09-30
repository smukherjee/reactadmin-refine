Configuration, testing and CI notes
=================================

This document explains how configuration is centralized in this project, how to run tests safely, and how to configure CI so tests are reproducible.

-Centralized configuration
-------------------------

- All runtime configuration is exposed via a single pydantic `Settings` class in `backend/app/core/config.py`.
- The project loads environment variables from an `.env` file (see `Settings.Config.env_file = ".env"`).
- A canonical example file is provided at the repository root: `.env.example`. Copy that to `.env` and edit values for your environment.

-Key settings you should know about
---------------------------------

- DATABASE_URL — SQLAlchemy connection string used by both sync and async engines. Example (Postgres):

  `postgresql+psycopg://postgres:postgres@localhost:5432/reactadmin_refine`

  Default development value is `sqlite:///./db/dev.db`.

- TEST_BASE_URL / FRONTEND_BASE_URL — URLs used by perf/security tooling and tests.
- SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES — auth settings used by JWT creation and verification.
- REDIS_URL, CACHE_TTL — cache and redis configuration.

Important testing note: set DATABASE_URL before importing the app
----------------------------------------------------------------

Some modules (notably `backend/app/db/core.py`) create SQLAlchemy engines at module import time. Tests and CI MUST set `DATABASE_URL` before importing any application module so the engines are created against the intended database.

Recommended pattern in tests and CI:

1. Set the environment variable (or write a `.env` file and load it) so `DATABASE_URL` is available.
2. Import or start the application (for example `from backend.main import app`) only after `DATABASE_URL` is set.

Example (pytest local run):

```bash
# Ensure DATABASE_URL points to a local test DB file (or a test Postgres instance) before running pytest
export DATABASE_URL=sqlite:///./tmp_test.db
pytest -q
```

Tests that mutate environment
----------------------------

Some tests mutate environment variables at runtime (for example, they set `ENVIRONMENT` or `TEST_BASE_URL`). The test suite uses a helper `reload_settings()` in `backend.app.core.config` to re-read environment variables into the module-level `settings` object. If you write tests that change env vars at runtime, call `reload_settings()` after modifying `os.environ` so the application sees the updated values.

Example:

```python
import os
from backend.app.core import config

os.environ['ENVIRONMENT'] = 'production'
config.reload_settings()
# Now backend.app.core.config.settings will reflect the production environment
```

CI guidance (GitHub Actions snippet)
----------------------------------

Set critical env vars before running pytest. The step that runs tests must have `DATABASE_URL` set in the environment so import-time engines are created against the intended database.

Minimal GitHub Actions job snippet:

```yaml
jobs:
  tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: reactadmin_refine_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres -d reactadmin_refine_test" \
          --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install -r backend/requirements.txt
      - name: Export test DB URL
        env:
          PG_HOST: localhost
          PG_PORT: 5432
        run: |
          echo "DATABASE_URL=postgresql+psycopg://postgres:postgres@${PG_HOST}:${PG_PORT}/reactadmin_refine_test" >> $GITHUB_ENV
      - name: Run backend tests
        working-directory: backend
        run: |
          pytest -q
```

Notes:

- The important step is to ensure `DATABASE_URL` is present in the environment before `pytest` (or any test-runner) imports application modules.
- You can also place configuration in a `.env` file and ensure your test runner loads it prior to import, but explicit environment export in CI steps is the most reliable approach.


Tooling: running OWASP/perf scripts
----------------------------------

- The OWASP and perf tools read `TEST_BASE_URL` and `FRONTEND_BASE_URL` from Settings. You can override them with environment variables or by copying `.env.example` to `.env` and editing values.

If you want to remove import-time side-effects entirely
----------------------------------------------------

- A longer-term improvement is to make resource creation (database engines, redis clients) lazy/factory-based, so they are only created when an explicit `init()` function is called. This avoids ordering constraints in tests and CI. This change is larger and can be done incrementally by introducing `get_engine()`/`get_async_engine()` helpers and updating callers.

If you'd like, I can implement the lazy/factory refactor (it requires updates across modules that currently import `engine`, `SessionLocal`, etc.).

---

If you want me to proceed with the lazy-engine refactor (no import-time engine creation) or to finish a final pass converting any remaining ad-hoc env reads into `settings` calls, tell me which and I'll implement it next.
