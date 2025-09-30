Enterprise-grade FastAPI backend — audit and recommended structure

This document audits the current `backend/` folder and provides a concrete, low-risk migration plan and checklist to bring the codebase to a maintainable, enterprise-grade layout.

Current tree (top-level files in `backend/`):

- .env.example
- __init__.py
- auth.py
- cache.py
- create_tables.py
- crud.py
- database.py
- main.py
- middleware.py
- models.py
- schemas.py
- tests/
- venv/
- requirements.txt, pyproject.toml, setup.cfg, pytest.ini, README.md, scripts/

Summary audit

- Single-package layout: The project places many app responsibilities at module-level files (e.g. `main.py`, `crud.py`, `auth.py`, `cache.py`, etc.). This is fine for small projects but becomes hard to maintain as the product grows.
- Missing clear separation of concerns: currently database, auth, caching, routers, and schemas are top-level modules. For enterprise apps we prefer a modular layout (routers, services, core/config, db, models, api versioning).
- Tests are present and succeed — excellent. Keep the tests and fixtures as you refactor.
- No migrations tooling detected (consider Alembic for schema migrations).
- No documentation folder (add docs, ADRs, architecture overview).
- No dedicated `app` package with router wiring and dependency injection separated from application module.
- No health/metrics endpoints or observability (prometheus metrics, structured logging) — recommended for production.

Enterprise-recommended structure

This structure scales well and is widely used in production FastAPI apps. Move files incrementally to match this layout:

backend/
  ├─ app/                      # new application package
  │   ├─ api/
  │   │   └─ v1/
  │   │       ├─ __init__.py   # exposes router(s)
  │   │       └─ auth.py       # routers for auth endpoints
  │   ├─ core/
  │   │   ├─ config.py         # pydantic BaseSettings for configuration
  │   │   ├─ security.py       # token helpers, password context
  │   │   └─ logging.py        # structured logging setup
  │   ├─ db/
  │   │   ├─ base.py           # Base declarative, session maker
  │   │   ├─ models/           # (optional) split models into multiple files
  │   │   └─ migrations/       # alembic config
  │   ├─ services/             # business logic separated from CRUD
  │   ├─ crud/                 # slim wrappers interacting with DB
  │   ├─ cache/                # caching helpers (redis) moved from cache.py
  │   ├─ auth/                 # auth logic (token creation, dependencies)
  │   ├─ middleware/           # middleware implementations
  │   ├─ schemas/              # pydantic schemas (or keep existing `schemas.py`)
  │   ├─ api_router.py         # central router that includes versioned routers
  │   └─ main.py               # creates FastAPI app, attaches routers & middleware
  ├─ tests/                    # keep tests; adjust imports to `from app...` if files are moved
  ├─ scripts/                  # utility scripts (run_checks.sh already present)
  ├─ alembic.ini               # if you add Alembic for migrations
  ├─ Dockerfile                # production container
  └─ README.md

Why this layout?
- Clear separation: `core` contains config and infra-level utilities, `api` contains HTTP surface, `services` and `crud` contain business logic and DB access respectively.
- Versioning: `api/v1` makes it easy to add v2 later without breaking clients.
- Testability: smaller modules are easier to unit-test.
- Maintainability: teams can own folders (auth team owns `app/auth`, infra team owns `app/cache`).

Concrete migration plan (incremental, low risk)

1) Create `app/` package alongside current modules (no file moves yet). Add `app/__init__.py` and `app/api/v1/__init__.py` as placeholders. Update tests to import via `backend` while you make changes.

2) Move functionality gradually:
   - Move small modules first (e.g., `cache.py` -> `app/cache/__init__.py`), update imports in a targeted way and run tests.
   - Then move `auth.py` and `crud.py` into `app/auth` and `app/crud` respectively.
   - Keep `main.py` as the app bootstrapping file; create `app/main.py` which imports from the other app modules and registers routers. For the short term, keep `backend/main.py` as compatibility wrapper that imports from `app.main`.

3) Add configuration via `pydantic.BaseSettings` in `app/core/config.py` and read environment variables from there. Replace ad-hoc os.getenv usage.

4) Add Alembic and database migration support; put migration scripts under `migrations/` and configure `alembic.ini`.

5) Add observability: a `GET /health` endpoint, metrics endpoint, structured logging, and Sentry/Tracing integration if needed.

6) Add production-ready Dockerfile, gunicorn/uvicorn entrypoint, and a GitHub Actions workflow that runs `scripts/run_checks.sh` on PRs.

7) Update tests to import from the new package paths and maintain fixtures. Run the test suite after each small move.

Checklist for enterprise readiness

- [ ] Modular package layout (api, core, db, services, auth, cache)
- [ ] Config via pydantic BaseSettings
- [ ] Database migrations (Alembic)
- [ ] CI pipeline running tests+typechecks (we added `scripts/run_checks.sh` and can scaffold GH workflow)
- [ ] Dependency management (pyproject.toml or pinned requirements.txt) — you have both; prefer pyproject + lockfile for reproducibility
- [ ] Dockerfile and container run instructions
- [ ] Health and metrics endpoints
- [ ] Structured logs and request/response logging
- [ ] Rate limiting and security headers via middleware (X-Frame-Options, CSP, HSTS)
- [ ] Secrets management guidance (do not store secrets in repo; use env or secret manager)
- [ ] RBAC and tenant isolation tests (we already have multitenant tests — great)

Minimal safe changes I can apply now

- Create `app/` skeleton directories so you can start migrating in small steps without breaking imports.
- Add `ARCHITECTURE.md` (this file) — done.
- Optionally scaffold `app/core/config.py` with a `BaseSettings` class so you can migrate from `os.getenv` in small increments.

Would you like me to:
1) Create the `app/` skeleton (api/v1, core, db, auth, cache, services, crud) as empty modules and a `app/main.py` that wraps `backend.main`? (lowest risk — I can keep current imports intact during migration)
2) Scaffold Alembic configuration and a basic `Dockerfile`?
3) Start moving one file (for example `cache.py`) into `app/cache` and update imports + tests iteratively?

Tell me which option you'd like and I'll implement it (I recommend #1 to get a clean, gradual migration path).