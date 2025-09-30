v1 package: sync (legacy) endpoints and shims
=============================================

- Purpose: `backend.app.api.v1` contains legacy synchronous endpoints (sync
  handlers) that remain available under the `/api/v1` prefix.
- The new async implementations live in `backend.app.api.v2` and are the
  authoritative code for async behavior.

Naming and shim policy
----------------------
- Files prefixed with `async_` belong to the async implementation set and
  should live under `backend/app/api/v2`.
- During migration we keep small shim modules in v1 that raise ImportError
  and point to the v2 module (filenames `moved_to_v2_*` or `async_*` shims).
- Do not import async implementations from `backend.app.api.v1` — import
  `backend.app.api.v2` modules instead.

If you want to promote a v2 async endpoint back into v1 (rare), rename the
file and ensure the exported router is included by `backend.app.api.v1.__init__`.
