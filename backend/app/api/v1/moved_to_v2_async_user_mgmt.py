"""Shim (moved): async user_mgmt moved to api.v2.

This file exists to indicate the async user management endpoints were moved to v2.
Importing this module will raise an ImportError directing developers to the
new location.
"""

raise ImportError("api.v1.async_user_mgmt has been moved to api.v2.async_user_mgmt")
