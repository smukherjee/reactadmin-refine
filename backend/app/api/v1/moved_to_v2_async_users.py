"""Shim (moved): async users moved to api.v2.

This file exists to indicate the async users endpoints were moved to v2.
Importing this module will raise an ImportError directing developers to the
new location to avoid confusion between sync v1 and async v2 implementations.
"""

raise ImportError("api.v1.async_users has been moved to api.v2.async_users")
