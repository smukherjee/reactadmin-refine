"""Async system metrics repository for system monitoring operations.

This module provides async system metrics collection including
health checks, performance monitoring, and system statistics.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
import time
import psutil
import asyncio
from datetime import datetime, timedelta

from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class AsyncSystemRepository:
    """Async repository for system metrics and monitoring operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health metrics."""
        try:
            # Get CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Get memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Get disk metrics
            disk_usage = psutil.disk_usage('/')
            
            # Get network metrics
            network_io = psutil.net_io_counters()
            
            # Get process info
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            # Calculate uptime
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": round(uptime_seconds, 2),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None
                },
                "memory": {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "usage_percent": memory.percent,
                    "swap_total": swap.total,
                    "swap_used": swap.used,
                    "swap_percent": swap.percent
                },
                "disk": {
                    "total_bytes": disk_usage.total,
                    "used_bytes": disk_usage.used,
                    "free_bytes": disk_usage.free,
                    "usage_percent": round((disk_usage.used / disk_usage.total) * 100, 2)
                },
                "network": {
                    "bytes_sent": network_io.bytes_sent,
                    "bytes_recv": network_io.bytes_recv,
                    "packets_sent": network_io.packets_sent,
                    "packets_recv": network_io.packets_recv
                },
                "process": {
                    "pid": process.pid,
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process_cpu,
                    "num_threads": process.num_threads(),
                    "create_time": process.create_time()
                }
            }
            
            # Determine overall health status
            if (cpu_percent > 90 or memory.percent > 90 or 
                disk_usage.used / disk_usage.total > 0.95):
                health_data["status"] = "warning"
            
            logger.info(f"System health check: CPU {cpu_percent}%, RAM {memory.percent}%")
            return health_data
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_database_health(self) -> Dict[str, Any]:
        """Get database connection and performance metrics."""
        try:
            # Test database connection
            from sqlalchemy import text
            start_time = time.time()
            result = await self.session.execute(text("SELECT 1"))
            connection_time = (time.time() - start_time) * 1000  # ms
            
            # Get basic database info
            db_info = {
                "status": "healthy",
                "connection_time_ms": round(connection_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                # Try to get more detailed database stats (SQLite specific)
                result = await self.session.execute(text("PRAGMA database_list"))
                databases = result.fetchall()
                db_info["databases"] = len(databases)
                
                # Get schema info
                result = await self.session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = result.fetchall()
                db_info["tables"] = len(tables)
                
            except Exception as e:
                logger.warning(f"Could not get detailed database info: {e}")
                db_info["warning"] = "Limited database info available"
            
            logger.info(f"Database health check: {connection_time:.2f}ms connection time")
            return db_info
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics and statistics."""
        try:
            # Get current process info
            process = psutil.Process()
            
            # Get file descriptor info
            try:
                num_fds = process.num_fds()
            except (AttributeError, OSError):
                num_fds = None  # Not available on Windows
            
            # Get connection info
            try:
                connections = process.connections()
                tcp_connections = len([c for c in connections if c.type.name == 'SOCK_STREAM'])
                udp_connections = len([c for c in connections if c.type.name == 'SOCK_DGRAM'])
            except (AttributeError, OSError):
                tcp_connections = None
                udp_connections = None
            
            metrics = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "process": {
                    "pid": process.pid,
                    "name": process.name(),
                    "status": process.status(),
                    "create_time": process.create_time(),
                    "num_threads": process.num_threads(),
                    "num_fds": num_fds,
                    "tcp_connections": tcp_connections,
                    "udp_connections": udp_connections
                },
                "memory": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms,
                    "percent": process.memory_percent()
                },
                "cpu": {
                    "percent": process.cpu_percent(),
                    "times": process.cpu_times()._asdict()
                }
            }
            
            logger.info("Application metrics collected successfully")
            return metrics
            
        except Exception as e:
            logger.error(f"Application metrics collection failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        try:
            # Collect various performance metrics
            start_time = time.time()
            
            # CPU load averages (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                load_data = {
                    "1min": load_avg[0],
                    "5min": load_avg[1],
                    "15min": load_avg[2]
                }
            except (AttributeError, OSError):
                load_data = None  # Not available on Windows
            
            # Disk I/O stats
            disk_io = psutil.disk_io_counters()
            
            # Network I/O stats
            net_io = psutil.net_io_counters()
            
            # CPU times
            cpu_times = psutil.cpu_times()
            
            collection_time = (time.time() - start_time) * 1000  # ms
            
            stats = {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "collection_time_ms": round(collection_time, 2),
                "load_average": load_data,
                "cpu_times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle
                },
                "disk_io": {
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_time": disk_io.read_time,
                    "write_time": disk_io.write_time
                } if disk_io else None,
                "network_io": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout
                } if net_io else None
            }
            
            logger.info(f"Performance stats collected in {collection_time:.2f}ms")
            return stats
            
        except Exception as e:
            logger.error(f"Performance stats collection failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check of all system components."""
        try:
            start_time = time.time()
            
            # Run all health checks concurrently
            system_task = asyncio.create_task(self.get_system_health())
            db_task = asyncio.create_task(self.get_database_health())
            app_task = asyncio.create_task(self.get_application_metrics())
            
            # Wait for all tasks to complete
            results = await asyncio.gather(
                system_task, db_task, app_task, return_exceptions=True
            )
            
            system_health, db_health, app_metrics = results
            total_time = (time.time() - start_time) * 1000  # ms
            
            # Determine overall status
            overall_status = "healthy"
            
            # Check for exceptions
            if any(isinstance(result, Exception) for result in results):
                overall_status = "error"
            else:
                # Check status of successful results
                statuses = []
                if isinstance(system_health, dict):
                    statuses.append(system_health.get("status", "unknown"))
                if isinstance(db_health, dict):
                    statuses.append(db_health.get("status", "unknown"))
                if isinstance(app_metrics, dict):
                    statuses.append(app_metrics.get("status", "unknown"))
                
                if any(status != "healthy" for status in statuses):
                    overall_status = "warning"
            
            health_check = {
                "overall_status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "check_duration_ms": round(total_time, 2),
                "system": system_health if not isinstance(system_health, Exception) else {"error": str(system_health)},
                "database": db_health if not isinstance(db_health, Exception) else {"error": str(db_health)},
                "application": app_metrics if not isinstance(app_metrics, Exception) else {"error": str(app_metrics)}
            }
            
            logger.info(f"Health check completed in {total_time:.2f}ms - Status: {overall_status}")
            return health_check
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


async def get_system_repository(session: AsyncSession) -> AsyncSystemRepository:
    """Factory function to create AsyncSystemRepository instance."""
    return AsyncSystemRepository(session)