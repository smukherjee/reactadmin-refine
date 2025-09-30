"""Compatibility shim: lazily forward to backend.app.schemas.core"""

from importlib import import_module
from types import ModuleType
from typing import Any

_REAL_MODULE = "backend.app.schemas.core"


def _load() -> ModuleType:
    return import_module(_REAL_MODULE)


def __getattr__(name: str) -> Any:  # pragma: no cover - exercised indirectly in tests
    mod = _load()
    return getattr(mod, name)


def __dir__():  # pragma: no cover - convenience helper
    mod = _load()
    return list(globals().keys()) + [n for n in dir(mod) if not n.startswith("_")]