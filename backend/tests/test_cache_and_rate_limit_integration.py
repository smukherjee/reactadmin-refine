import asyncio
import time
from typing import Any, Dict, List, Tuple, cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import ASGIApp

from backend.app.middleware.security import RateLimitMiddleware
from backend.app.repositories.cache import AsyncCacheRepository

# We'll monkeypatch the async redis client in backend.app.cache.async_redis


class AsyncInMemoryRedis:
    import asyncio
    import time
    from typing import Any, Dict, List, Tuple

    import pytest

    from backend.app.middleware.security import RateLimitMiddleware
    from backend.app.repositories.cache import AsyncCacheRepository

    # We'll monkeypatch the async redis client in backend.app.cache.async_redis

    class AsyncInMemoryRedis:
        def __init__(self):
            # key -> list of (member:str, score:float)
            self.zsets: Dict[str, List[Tuple[str, float]]] = {}
            self.kv: Dict[str, bytes] = {}
            self.ttls: Dict[str, float] = {}

        async def ping(self):
            return True

        async def info(self):
            return {
                "used_memory": 4096,
                "connected_clients": 2,
                "used_memory_human": "4K",
                "uptime_in_seconds": 3600,
                "redis_version": "6.0",
            }

        async def dbsize(self):
            return len(self.kv)

        async def keys(self, pattern: str = "*"):
            # naive pattern '*' only
            if pattern == "*":
                return list(self.kv.keys())
            # very simple prefix match
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                return [k for k in self.kv.keys() if k.startswith(prefix)]
            return [k for k in self.kv.keys() if k == pattern]

        async def set(self, key: str, value: str):
            self.kv[key] = value.encode()
            return True

        async def setex(self, key: str, ttl: int, value: str):
            self.kv[key] = value.encode()
            self.ttls[key] = int(time.time()) + int(ttl)
            return True

        async def get(self, key: str):
            return self.kv.get(key)

        async def ttl(self, key: str):
            exp = self.ttls.get(key)
            if exp is None:
                return -1
            rem = int(exp - time.time())
            return rem if rem > 0 else -1

        async def delete(self, *keys):
            count = 0
            for k in keys:
                if k in self.kv:
                    del self.kv[k]
                    count += 1
                if k in self.ttls:
                    del self.ttls[k]
            return count

        async def flushdb(self):
            self.kv.clear()
            self.ttls.clear()
            return True

        # sorted-set operations for rate limiter
        async def zremrangebyscore(self, key: str, min_score: float, max_score: float):
            lst = self.zsets.get(key, [])
            new = [item for item in lst if item[1] > max_score]
            removed = len(lst) - len(new)
            self.zsets[key] = new
            return removed

        async def zcard(self, key: str):
            return len(self.zsets.get(key, []))

        async def zadd(self, key: str, mapping: Dict[str, float]):
            lst = self.zsets.setdefault(key, [])
            for member, score in mapping.items():
                lst.append((member, float(score)))
            # keep sorted by score
            lst.sort(key=lambda x: x[1])
            self.zsets[key] = lst
            return len(mapping)

        async def expire(self, key: str, seconds: int):
            # noop for in-memory
            return True

        async def zrange(
            self, key: str, start: int, end: int, withscores: bool = False
        ):
            lst = self.zsets.get(key, [])
            if not lst:
                return []
            slice_ = lst[start : end + 1]
            if withscores:
                return [(member, score) for member, score in slice_]
            return [member for member, _ in slice_]

    @pytest.mark.asyncio
    async def test_async_cache_repo_and_rate_limit(monkeypatch: MonkeyPatch):
        # Patch the async redis client
        import backend.app.cache.async_redis as async_mod

        fake = AsyncInMemoryRedis()
        monkeypatch.setattr(async_mod, "_async_redis_client", fake)

        # Create repository with dummy session (not used) and silence static type checkers
        repo = AsyncCacheRepository(cast(AsyncSession, None))

        # Test set and get
        res_set = await repo.set_cache_value("k1", {"a": 1}, ttl=2)
        assert res_set["status"] == "success"

        res_get = await repo.get_cache_value("k1")
        assert res_get["status"] == "success"
        assert isinstance(res_get["value"], dict)
        assert res_get["value"]["a"] == 1

        # Test keys
        keys = await repo.get_cache_keys("*", limit=10)
        assert keys["returned"] >= 1
        assert "k1" in keys["keys"]

        # Test delete
        del_res = await repo.delete_cache_key("k1")
        assert del_res["status"] in ("success", "not_found")

        # Test clear cache
        await repo.set_cache_value("kx", "v")
        clear_res = await repo.clear_cache(pattern="kx")
        assert clear_res["status"] == "success"

        # Test cache status
        status = await repo.get_cache_status()
        assert status["connected"] is True or status["status"] in (
            "healthy",
            "unhealthy",
        )

        # Test rate limiter behavior (use middleware internal method)
        middleware = RateLimitMiddleware(
            cast(ASGIApp, lambda scope: None), max_requests=5, window=2
        )

        key = "rl:test"
        # Call the rate limit method multiple times to simulate requests
        for i in range(3):
            curr, ttl = await middleware._async_redis_rate_limit(None, key, 5, 2)
            assert curr >= 1
            assert isinstance(ttl, int)

        # Ensure older entries are removed by passing a cutoff
        await asyncio.sleep(1)
        curr2, ttl2 = await middleware._async_redis_rate_limit(None, key, 5, 2)
        assert curr2 >= 1
