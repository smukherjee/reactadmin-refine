import asyncio
import time

import pytest

from backend.app.cache import core as cache_core


class FakeRedis:
    def __init__(self, delay=0.0, info=None):
        self.delay = delay
        self._info = info or {"used_memory": 1024, "connected_clients": 1}

    def ping(self):
        if self.delay:
            time.sleep(self.delay)
        return True

    def info(self):
        if self.delay:
            time.sleep(self.delay)
        return self._info


@pytest.mark.parametrize(
    "delay,timeout,expected_ok",
    [
        (0.0, 0.25, True),
        (0.5, 0.25, False),
    ],
)
def test_safe_redis_call_sync(monkeypatch, delay, timeout, expected_ok):
    fake = FakeRedis(delay=delay)

    monkeypatch.setattr(cache_core, "redis_client", fake)

    resp = cache_core.safe_redis_call(lambda c: c.ping(), timeout=timeout)
    assert resp.get("ok") == expected_ok


@pytest.mark.asyncio
async def test_async_safe_redis_call(monkeypatch):
    # Import async module lazily to ensure test environment
    from backend.app.cache import async_redis as async_mod

    class AsyncFake:
        def __init__(self, delay=0.0, info=None):
            self.delay = delay
            self._info = info or {"used_memory": 2048}

        async def ping(self):
            if self.delay:
                await asyncio.sleep(self.delay)
            return True

        async def info(self):
            if self.delay:
                await asyncio.sleep(self.delay)
            return self._info

        async def dbsize(self):
            return 5

    # Case: client not initialized
    monkeypatch.setattr(async_mod, "_async_redis_client", None)
    resp = await async_mod.async_safe_redis_call(lambda c: c.ping(), timeout=0.1)
    assert resp["ok"] is False
    assert "not initialized" in resp["error"]

    # Case: client exists and responds quickly
    monkeypatch.setattr(async_mod, "_async_redis_client", AsyncFake(delay=0.0))
    resp2 = await async_mod.async_safe_redis_call(lambda c: c.ping(), timeout=0.5)
    assert resp2["ok"] is True

    # Case: client exists but times out
    monkeypatch.setattr(async_mod, "_async_redis_client", AsyncFake(delay=0.5))
    resp3 = await async_mod.async_safe_redis_call(lambda c: c.ping(), timeout=0.1)
    assert resp3["ok"] is False and resp3["timeout"] is True
