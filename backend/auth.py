"""Backward-compatibility shim for auth helpers.

This module re-exports the moved implementation at `app.auth.core` so existing
imports remain functional while we migrate code into `app/`.
"""

from .app.auth.core import *  # noqa: F401,F403

