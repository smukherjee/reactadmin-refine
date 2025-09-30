"""Shim (moved): async tenants/audit moved to api.v2.

This file exists to indicate the async tenants/audit endpoints were moved to v2.
Importing this module will raise an ImportError directing developers to the
new location.
"""

raise ImportError("api.v1.async_tenants_audit has been moved to api.v2.async_tenants_audit")
