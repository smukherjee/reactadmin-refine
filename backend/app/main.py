"""Application wiring for versioned APIs.

This file is a migration target for `backend/main.py`. It demonstrates how to register routers
for API versioning and attach middleware. Move routing and startup logic here incrementally.
"""

from fastapi import FastAPI

from .api.v1 import router as v1_router

app = FastAPI(title="ReactAdmin-Refine Backend (app.main)")

# Register versioned v1 router under /api/v1
app.include_router(v1_router, prefix="/api/v1")


# Example: include a health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}
