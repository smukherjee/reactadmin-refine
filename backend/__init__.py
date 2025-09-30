"""Backend package initializer.

During the migration we provide a thin compatibility layer so imports such as
`from backend import main` continue to work while the real implementation
lives under `backend.app.*`.

This module re-exports the top-level shim modules that forward to
`backend.app` so existing import sites keep working until the shims are
removed.
"""

# Keep this module minimal to avoid importing submodules at package import
# time. Import hooks (PEP 562) or explicit `import backend.main` are used by the
# test harness which expects `backend.main` to be a shim module that lazily
# forwards to `backend.app.main.core`.

__all__ = []
