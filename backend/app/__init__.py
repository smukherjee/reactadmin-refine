"""Application migration package.

This package is used as a staging area while modules are moved from the
top-level `backend` package into `backend.app`. We intentionally avoid eager
imports here to keep startup fast during tests; individual modules are
imported where needed.
"""

# Expose nothing by default to avoid static analysis warnings about names
# that are present as subpackages on disk but not imported here.
__all__: list[str] = []
