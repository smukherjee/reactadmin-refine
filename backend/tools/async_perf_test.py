#!/usr/bin/env python3
"""Async performance test (moved to tools/ to avoid pytest collection)

This file was moved from the repository root into tools/ so pytest won't
collect it as a test. Run it manually when you want to run perf checks.
"""
import asyncio
import time

import aiohttp


async def main():
    try:
        from backend.app.core.config import settings

        url = settings.TEST_BASE_URL
    except Exception:
        # Default to local backend for tool runs
        url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        t0 = time.time()
        async with session.get(url) as r:
            print("status", r.status)
            await r.text()
        print("elapsed", time.time() - t0)


if __name__ == "__main__":
    asyncio.run(main())
