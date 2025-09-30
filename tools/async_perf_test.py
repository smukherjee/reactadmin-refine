#!/usr/bin/env python3
"""Async performance test (moved to tools/ to avoid pytest collection)

This file was moved from the repository root into tools/ so pytest won't
collect it as a test. Run it manually when you want to run perf checks.
"""
import asyncio
import aiohttp
import time

async def main():
    url = "http://localhost:8000"
    async with aiohttp.ClientSession() as session:
        t0 = time.time()
        async with session.get(url) as r:
            print("status", r.status)
            await r.text()
        print("elapsed", time.time() - t0)

if __name__ == '__main__':
    asyncio.run(main())
