"""Database connection health checking implementation."""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncpg

from ..entities.database_protocols import ConnectionHealthChecker, ConnectionManager
from ..entities.database_connection import DatabaseConnection
from ....config.constants import HealthStatus
from ....core.exceptions.database import HealthCheckFailedError

logger = logging.getLogger(__name__)


class DatabaseHealthChecker(ConnectionHealthChecker):
    """Implementation of ConnectionHealthChecker for database connections."""
    
    def __init__(self, 
                 connection_timeout: int = 10,
                 query_timeout: int = 5,
                 health_check_interval: int = 30):
        self.connection_timeout = connection_timeout
        self.query_timeout = query_timeout
        self.health_check_interval = health_check_interval
        
        # Health check queries by connection type
        self.health_check_queries = {
            "basic": "SELECT 1",
            "extended": "SELECT current_timestamp, version()",
            "deep": """
                SELECT 
                    current_timestamp as check_time,
                    pg_database_size(current_database()) as db_size,
                    (SELECT count(*) FROM pg_stat_activity) as active_connections,
                    pg_is_in_recovery() as is_replica
            """
        }
    
    async def check_health(self, connection: DatabaseConnection) -> bool:
        """Check if a database connection is healthy."""
        try:
            health_status = await self.get_health_status(connection)
            return health_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        except Exception as e:
            logger.error(f"Health check failed for {connection.connection_name}: {e}")
            return False
    
    async def get_health_status(self, connection: DatabaseConnection) -> HealthStatus:
        """Get detailed health status for a connection."""
        if not connection.is_active:
            return HealthStatus.UNHEALTHY
        
        try:
            # Perform basic connectivity check
            basic_check = await self._perform_basic_check(connection)
            if not basic_check:
                return HealthStatus.UNHEALTHY
            
            # Perform extended health check
            extended_check = await self._perform_extended_check(connection)
            if not extended_check:
                return HealthStatus.DEGRADED
            
            # Check if there have been recent failures
            if connection.consecutive_failures > 0:
                if connection.consecutive_failures >= connection.max_consecutive_failures // 2:
                    return HealthStatus.DEGRADED
            
            return HealthStatus.HEALTHY
            
        except Exception as e:
            logger.error(f"Health status check failed for {connection.connection_name}: {e}")
            return HealthStatus.UNHEALTHY
    
    async def _perform_basic_check(self, connection: DatabaseConnection) -> bool:
        """Perform basic connectivity check."""
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database_name,
                    user=connection.username,
                    password=connection.encrypted_password,  # Password should be decrypted at connection loading
                    ssl=connection.ssl_mode,
                ),
                timeout=self.connection_timeout
            )
            
            try:
                # Execute basic health check query
                result = await asyncio.wait_for(
                    conn.fetchval(self.health_check_queries["basic"]),
                    timeout=self.query_timeout
                )
                
                return result == 1
                
            finally:
                await conn.close()
                
        except asyncio.TimeoutError:
            logger.warning(f"Basic health check timed out for {connection.connection_name}")
            return False
        except Exception as e:
            logger.warning(f"Basic health check failed for {connection.connection_name}: {e}")
            return False
    
    async def _perform_extended_check(self, connection: DatabaseConnection) -> bool:
        """Perform extended health check with more detailed queries."""
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database_name,
                    user=connection.username,
                    password=connection.encrypted_password,  # Password should be decrypted at connection loading
                    ssl=connection.ssl_mode,
                ),
                timeout=self.connection_timeout
            )
            
            try:
                # Execute extended health check query
                result = await asyncio.wait_for(
                    conn.fetchrow(self.health_check_queries["extended"]),
                    timeout=self.query_timeout
                )
                
                if result:
                    # Check if we can get current timestamp (basic functionality)
                    current_time = result['current_timestamp']
                    version_info = result['version']
                    
                    # Validate results
                    if current_time and version_info:
                        return True
                
                return False
                
            finally:
                await conn.close()
                
        except asyncio.TimeoutError:
            logger.warning(f"Extended health check timed out for {connection.connection_name}")
            return False
        except Exception as e:
            logger.warning(f"Extended health check failed for {connection.connection_name}: {e}")
            return False
    
    async def perform_deep_health_check(self, connection: DatabaseConnection) -> Dict[str, any]:
        """Perform deep health check with detailed metrics."""
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database_name,
                    user=connection.username,
                    password=connection.encrypted_password,  # Password should be decrypted at connection loading
                    ssl=connection.ssl_mode,
                ),
                timeout=self.connection_timeout
            )
            
            try:
                # Execute deep health check query
                result = await asyncio.wait_for(
                    conn.fetchrow(self.health_check_queries["deep"]),
                    timeout=self.query_timeout * 2  # Allow more time for deep check
                )
                
                if result:
                    return {
                        "status": "healthy",
                        "check_time": result['check_time'],
                        "database_size_bytes": result['db_size'],
                        "active_connections": result['active_connections'],
                        "is_replica": result['is_replica'],
                        "response_time_ms": 0,  # TODO: Measure actual response time
                    }
                else:
                    return {"status": "unhealthy", "error": "No result from deep check query"}
                
            finally:
                await conn.close()
                
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy", 
                "error": f"Deep health check timed out after {self.query_timeout * 2}s"
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_schema_accessibility(self, connection: DatabaseConnection, schema_name: str) -> bool:
        """Check if a specific schema is accessible."""
        try:
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database_name,
                    user=connection.username,
                    password=connection.encrypted_password,
                    ssl=connection.ssl_mode,
                ),
                timeout=self.connection_timeout
            )
            
            try:
                # Check if schema exists and is accessible
                query = """
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = $1
                    )
                """
                
                result = await asyncio.wait_for(
                    conn.fetchval(query, schema_name),
                    timeout=self.query_timeout
                )
                
                return bool(result)
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.warning(f"Schema accessibility check failed for {schema_name}: {e}")
            return False
    
    async def measure_connection_latency(self, connection: DatabaseConnection) -> Optional[float]:
        """Measure connection latency in milliseconds."""
        try:
            start_time = datetime.utcnow()
            
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=connection.host,
                    port=connection.port,
                    database=connection.database_name,
                    user=connection.username,
                    password=connection.encrypted_password,
                    ssl=connection.ssl_mode,
                ),
                timeout=self.connection_timeout
            )
            
            try:
                # Execute simple query and measure time
                await asyncio.wait_for(
                    conn.fetchval("SELECT 1"),
                    timeout=self.query_timeout
                )
                
                end_time = datetime.utcnow()
                latency_ms = (end_time - start_time).total_seconds() * 1000
                
                return latency_ms
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.warning(f"Latency measurement failed for {connection.connection_name}: {e}")
            return None


class ContinuousHealthMonitor:
    """Continuous health monitoring for database connections."""
    
    def __init__(self, 
                 health_checker: ConnectionHealthChecker,
                 registry,  # ConnectionRegistry - avoiding circular import
                 check_interval: int = 30):
        self.health_checker = health_checker
        self.registry = registry
        self.check_interval = check_interval
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._stop_event.clear()
            self._monitoring_task = asyncio.create_task(self._monitor_loop())
            logger.info("Started continuous health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        self._stop_event.set()
        
        if self._monitoring_task and not self._monitoring_task.done():
            try:
                await asyncio.wait_for(self._monitoring_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Stopped continuous health monitoring")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                await self._check_all_connections()
                
                # Wait for next check interval or stop event
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.check_interval
                    )
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue monitoring
                    
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                # Wait a bit before retrying
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=10  # Wait 10 seconds before retry
                    )
                    break
                except asyncio.TimeoutError:
                    continue
    
    async def _check_all_connections(self) -> None:
        """Check health of all registered connections."""
        try:
            connections = await self.registry.list_connections(active_only=True)
            
            if not connections:
                return
            
            # Check connections in parallel
            tasks = []
            for connection in connections:
                task = self._check_single_connection(connection)
                tasks.append(task)
            
            # Wait for all health checks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                connection = connections[i]
                
                if isinstance(result, Exception):
                    logger.error(f"Health check error for {connection.connection_name}: {result}")
                    await self._handle_unhealthy_connection(connection)
                elif not result:
                    await self._handle_unhealthy_connection(connection)
                else:
                    await self._handle_healthy_connection(connection)
                    
        except Exception as e:
            logger.error(f"Error checking all connections: {e}")
    
    async def _check_single_connection(self, connection: DatabaseConnection) -> bool:
        """Check health of a single connection."""
        try:
            return await self.health_checker.check_health(connection)
        except Exception as e:
            logger.error(f"Health check failed for {connection.connection_name}: {e}")
            return False
    
    async def _handle_healthy_connection(self, connection: DatabaseConnection) -> None:
        """Handle a healthy connection."""
        if not connection.is_healthy:
            logger.info(f"Connection {connection.connection_name} is now healthy")
            connection.mark_healthy()
            await self.registry.update_connection(connection)
    
    async def _handle_unhealthy_connection(self, connection: DatabaseConnection) -> None:
        """Handle an unhealthy connection."""
        connection.increment_failure_count()
        
        if connection.consecutive_failures >= connection.max_consecutive_failures:
            logger.warning(
                f"Connection {connection.connection_name} marked as unhealthy "
                f"after {connection.consecutive_failures} consecutive failures"
            )
            connection.mark_unhealthy("Continuous health check failures")
        
        await self.registry.update_connection(connection)