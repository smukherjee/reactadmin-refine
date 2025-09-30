from typing import Optional

from backend.app.cache import core as cache_core
from backend.app.db.core import get_engine, init_async_engine


def init_app(database_url: Optional[str] = None) -> None:
    """Initialize application resources synchronously where possible.

    This helper initializes the synchronous DB engine and the redis cache client
    (synchronous client). Async initializers (like `init_async_redis`) are left to
    the async startup path.
    """
    # Initialize sync DB engine (if not already)
    # Initialize sync DB engine (if not already). If callers pass an explicit
    # database_url in the future we could wire it through, but for now the
    # module-level getters read settings and are sufficient.
    get_engine()

    # Initialize synchronous Redis client if available (best-effort, bounded)
    try:
        # attempt a safe ping to initialize the client without blocking startup
        try:
            cache_core.safe_redis_call(lambda c: c.ping(), timeout=0.25)
        except Exception:
            # ignore timing/availability errors during best-effort init
            pass
    except Exception:
        # best-effort: if cache init fails, continue; errors will surface at runtime
        pass
