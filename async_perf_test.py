#!/usr/bin/env python3
"""Simple performance test for async API endpoints."""
import asyncio
import time
import aiohttp
import json
from typing import List

async def test_endpoint(session: aiohttp.ClientSession, url: str) -> dict:
    """Test a single endpoint and measure response time."""
    start_time = time.time()
    try:
        async with session.get(url) as response:
            content = await response.text()
            duration_ms = (time.time() - start_time) * 1000
            return {
                "url": url,
                "status": response.status,
                "duration_ms": round(duration_ms, 2),
                "success": response.status < 400
            }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "url": url,
            "status": 0,
            "duration_ms": round(duration_ms, 2),
            "success": False,
            "error": str(e)
        }

async def run_concurrent_requests(base_url: str, endpoints: List[str], concurrency: int = 10, iterations: int = 5):
    """Run concurrent requests to test performance."""
    print(f"Testing {len(endpoints)} endpoints with {concurrency} concurrent requests, {iterations} iterations each")
    
    connector = aiohttp.TCPConnector(limit=50)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        all_tasks = []
        
        # Create tasks for all requests
        for i in range(iterations):
            for endpoint in endpoints:
                url = f"{base_url}{endpoint}"
                tasks_batch = [test_endpoint(session, url) for _ in range(concurrency)]
                all_tasks.extend(tasks_batch)
        
        print(f"Running {len(all_tasks)} total requests...")
        start_time = time.time()
        
        # Run all requests concurrently
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Process results
        successful = 0
        failed = 0
        total_response_time = 0
        response_times = []
        
        for result in results:
            if isinstance(result, dict):
                if result["success"]:
                    successful += 1
                    total_response_time += result["duration_ms"]
                    response_times.append(result["duration_ms"])
                else:
                    failed += 1
            else:
                failed += 1
        
        # Calculate statistics
        if response_times:
            avg_response_time = total_response_time / len(response_times)
            response_times.sort()
            p50 = response_times[len(response_times) // 2]
            p95 = response_times[int(len(response_times) * 0.95)]
            p99 = response_times[int(len(response_times) * 0.99)]
            min_response = min(response_times)
            max_response = max(response_times)
        else:
            avg_response_time = p50 = p95 = p99 = min_response = max_response = 0
        
        requests_per_second = len(all_tasks) / total_duration if total_duration > 0 else 0
        
        print(f"\n=== Performance Test Results ===")
        print(f"Total Requests: {len(all_tasks)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Requests/Second: {requests_per_second:.2f}")
        print(f"\nResponse Times (ms):")
        print(f"  Average: {avg_response_time:.2f}")
        print(f"  Min: {min_response:.2f}")
        print(f"  Max: {max_response:.2f}")
        print(f"  50th percentile (P50): {p50:.2f}")
        print(f"  95th percentile (P95): {p95:.2f}")
        print(f"  99th percentile (P99): {p99:.2f}")
        
        return {
            "total_requests": len(all_tasks),
            "successful": successful,
            "failed": failed,
            "duration_seconds": total_duration,
            "requests_per_second": requests_per_second,
            "avg_response_time_ms": avg_response_time,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99
        }

async def main():
    base_url = "http://127.0.0.1:8001"
    
    # Test both sync and async endpoints
    endpoints = [
        "/health",
        "/health/detailed", 
        "/metrics",
        "/api/v1/info"
    ]
    
    print("🚀 Running async API performance test...")
    results = await run_concurrent_requests(base_url, endpoints, concurrency=5, iterations=3)
    
    print(f"\n✅ Test completed!")
    print(f"🔥 Achieved {results['requests_per_second']:.1f} requests/second")
    print(f"⚡ Average response time: {results['avg_response_time_ms']:.1f}ms")
    print(f"📊 95th percentile: {results['p95_ms']:.1f}ms")

if __name__ == "__main__":
    asyncio.run(main())