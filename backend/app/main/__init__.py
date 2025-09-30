"""app.main package initializer for the incremental migration.

This file exists so `import backend.app.main.core` works while we move
`backend/main.py` into `backend.app.main.core`.
"""

from .core import app  # re-export for convenience

__all__ = ["app"]
