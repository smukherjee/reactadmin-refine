Alembic (migrations) - backend only
===================================

This project keeps Alembic configuration and migrations inside the `backend/` folder to
avoid creating any files at the repository root.

Quick usage (from repository root):

```bash
# run alembic using the backend python environment
cd backend
/.venv/bin/alembic upgrade head
```

Notes:
- The `backend/alembic/env.py` reads the database URL from `backend.app.core.config.settings.DATABASE_URL` if present.
- The initial migration is intentionally empty; add schema changes using `alembic revision --autogenerate -m "..."`.
