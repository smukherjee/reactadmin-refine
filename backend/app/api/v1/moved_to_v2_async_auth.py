"""Shim (moved): async auth moved to api.v2.

This file exists to indicate the async auth endpoints were moved to v2.
Importing this module will raise an ImportError directing developers to the
new location.
"""

raise ImportError("api.v1.async_auth has been moved to api.v2.async_auth")
