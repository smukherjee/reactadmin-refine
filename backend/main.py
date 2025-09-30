"""Main application entry point.

This module provides the main FastAPI application instance from the modular
backend.app structure. Use this for running the server or importing the app.
"""

from backend.app.main.core import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)