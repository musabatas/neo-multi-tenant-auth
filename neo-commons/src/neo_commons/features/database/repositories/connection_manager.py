"""Database connection manager implementation."""

import asyncio
import logging
from typing import Dict, Optional, List, Any, AsyncContextManager
from contextlib import asynccontextmanager
import asyncpg
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..entities.database_protocols import (
    ConnectionManager, 
    ConnectionPool, 
    ConnectionRegistry,
    ConnectionHealthChecker,
    FailoverManager
)
from ..entities.database_connection import DatabaseConnection
from ....core.value_objects.identifiers import DatabaseConnectionId, RegionId
from ....config.constants import ConnectionType, HealthStatus
from ..entities.config import DatabaseConnectionConfig
from ....core.exceptions.database import (
    ConnectionNotFoundError,
    ConnectionPoolError,
    HealthCheckFailedError,
    FailoverError
)

logger = logging.getLogger(__name__)


@dataclass
class PoolMetrics:
    """Metrics for connection pool."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    last_health_check: Optional[datetime] = None
    total_queries: int = 0
    failed_queries: int = 0
    avg_response_time_ms: float = 0.0


class AsyncConnectionPool(ConnectionPool):
    """Implementation of ConnectionPool using asyncpg."""
    
    def __init__(self, connection: DatabaseConnection):
        self._connection_config = connection
        self._pool: Optional[asyncpg.Pool] = None
        self._metrics = PoolMetrics()
        self._is_closing = False
        self._lock = asyncio.Lock()
    
    async def _create_pool(self) -> asyncpg.Pool:
        """Create the asyncpg connection pool."""
        try:
            pool = await asyncpg.create_pool(
                host=self._connection_config.host,
                port=self._connection_config.port,
                database=self._connection_config.database_name,
                user=self._connection_config.username,
                password=self._connection_config.encrypted_password,  # Password should be decrypted at connection loading
                ssl=self._connection_config.ssl_mode,
                min_size=self._connection_config.pool_min_size,
                max_size=self._connection_config.pool_max_size,
                timeout=self._connection_config.pool_timeout_seconds,
                max_inactive_connection_lifetime=self._connection_config.pool_recycle_seconds,
            )
            
            logger.info(
                f"Created connection pool for {self._connection_config.connection_name}: "
                f"min={self._connection_config.pool_min_size}, "
                f"max={self._connection_config.pool_max_size}"
            )
            
            return pool
            
        except Exception as e:
            logger.error(
                f"Failed to create pool for {self._connection_config.connection_name}: {e}"
            )
            raise ConnectionPoolError(f"Failed to create connection pool: {e}")
    
    async def _ensure_pool(self) -> asyncpg.Pool:
        """Ensure the pool is created and available."""
        if self._pool is None:
            async with self._lock:
                if self._pool is None:  # Double-check
                    self._pool = await self._create_pool()
        return self._pool
    
    async def acquire_connection(self) -> asyncpg.Connection:
        """Acquire a connection from the pool."""
        if self._is_closing:
            raise ConnectionPoolError("Pool is closing")
        
        pool = await self._ensure_pool()
        
        try:
            conn = await pool.acquire(timeout=self._connection_config.pool_timeout_seconds)
            self._metrics.active_connections += 1
            return conn
        except Exception as e:
            logger.error(f"Failed to acquire connection: {e}")
            raise ConnectionPoolError(f"Failed to acquire connection: {e}")
    
    async def release_connection(self, connection: asyncpg.Connection) -> None:
        """Release a connection back to the pool."""
        if self._pool and not self._is_closing:
            try:
                await self._pool.release(connection)
                self._metrics.active_connections = max(0, self._metrics.active_connections - 1)
            except Exception as e:
                logger.warning(f"Error releasing connection: {e}")
    
    @asynccontextmanager
    async def connection(self) -> AsyncContextManager[asyncpg.Connection]:
        """Get a connection within a context manager."""
        conn = await self.acquire_connection()
        try:
            yield conn
        finally:
            await self.release_connection(conn)
    
    async def close(self) -> None:
        """Close the connection pool."""
        self._is_closing = True
        
        if self._pool:
            async with self._lock:
                if self._pool:
                    await self._pool.close()
                    self._pool = None
                    logger.info(f"Closed connection pool for {self._connection_config.connection_name}")
    
    async def is_healthy(self) -> bool:
        """Check if the pool is healthy."""
        if self._is_closing or not self._pool:
            return False
        
        try:
            async with self.connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Pool health check failed: {e}")
            return False
    
    @property
    def size(self) -> int:
        """Get current pool size."""
        if self._pool:
            return self._pool.get_size()
        return 0
    
    @property
    def free_size(self) -> int:
        """Get number of free connections in pool."""
        if self._pool:
            return self._pool.get_size() - self._pool.get_busy_count()
        return 0
    
    @property
    def metrics(self) -> PoolMetrics:
        """Get pool metrics."""
        if self._pool:
            self._metrics.total_connections = self._pool.get_size()
            self._metrics.idle_connections = self.free_size
        return self._metrics


class DatabaseConnectionManager(ConnectionManager):
    """Implementation of ConnectionManager."""
    
    def __init__(self, 
                 registry: ConnectionRegistry,
                 health_checker: ConnectionHealthChecker,
                 failover_manager: Optional[FailoverManager] = None):
        self._registry = registry
        self._health_checker = health_checker
        self._failover_manager = failover_manager
        self._pools: Dict[str, AsyncConnectionPool] = {}
        self._lock = asyncio.Lock()
    
    async def get_pool(self, connection_name: str) -> ConnectionPool:
        """Get or create a connection pool for the given connection."""
        if connection_name in self._pools:
            return self._pools[connection_name]
        
        async with self._lock:
            # Double-check pattern
            if connection_name in self._pools:
                return self._pools[connection_name]
            
            # Get connection configuration
            connection = await self._registry.get_connection_by_name(connection_name)
            if not connection:
                raise ConnectionNotFoundError(f"Connection '{connection_name}' not found")
            
            if not connection.is_available:
                raise ConnectionPoolError(f"Connection '{connection_name}' is not available")
            
            # Create new pool
            pool = AsyncConnectionPool(connection)
            self._pools[connection_name] = pool
            
            logger.info(f"Created new pool for connection: {connection_name}")
            return pool
    
    @asynccontextmanager
    async def get_connection(self, connection_name: str) -> AsyncContextManager[asyncpg.Connection]:
        """Get a database connection from the pool."""
        pool = await self.get_pool(connection_name)
        
        async with pool.connection() as conn:
            yield conn
    
    async def execute_query(self, 
                           connection_name: str, 
                           query: str, 
                           *args: Any) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        start_time = datetime.utcnow()
        
        try:
            async with self.get_connection(connection_name) as conn:
                rows = await conn.fetch(query, *args)
                
                # Convert to list of dicts
                results = [dict(row) for row in rows]
                
                # Log performance
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                if duration_ms > 100:  # Log slow queries
                    logger.warning(
                        f"Slow query ({duration_ms:.2f}ms) on {connection_name}: {query[:100]}..."
                    )
                
                return results
                
        except Exception as e:
            # Update connection failure count if we have failover manager
            if self._failover_manager:
                connection = await self._registry.get_connection_by_name(connection_name)
                if connection:
                    await self._failover_manager.notify_connection_failure(connection, e)
            
            logger.error(f"Query failed on {connection_name}: {e}")
            raise
    
    async def execute_fetchrow(self, 
                              connection_name: str, 
                              query: str, 
                              *args: Any) -> Optional[Dict[str, Any]]:
        """Execute a query and return single row."""
        try:
            async with self.get_connection(connection_name) as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Fetchrow failed on {connection_name}: {e}")
            raise
    
    async def execute_fetchval(self, 
                              connection_name: str, 
                              query: str, 
                              *args: Any) -> Any:
        """Execute a query and return single value."""
        try:
            async with self.get_connection(connection_name) as conn:
                return await conn.fetchval(query, *args)
                
        except Exception as e:
            logger.error(f"Fetchval failed on {connection_name}: {e}")
            raise
    
    async def execute_command(self, 
                             connection_name: str, 
                             command: str, 
                             *args: Any) -> str:
        """Execute a command (INSERT, UPDATE, DELETE) and return status."""
        try:
            async with self.get_connection(connection_name) as conn:
                return await conn.execute(command, *args)
                
        except Exception as e:
            logger.error(f"Command failed on {connection_name}: {e}")
            raise
    
    async def close_pool(self, connection_name: str) -> None:
        """Close a specific connection pool."""
        if connection_name in self._pools:
            pool = self._pools.pop(connection_name)
            await pool.close()
            logger.info(f"Closed pool for connection: {connection_name}")
    
    async def close_all_pools(self) -> None:
        """Close all connection pools."""
        async with self._lock:
            close_tasks = []
            for connection_name, pool in self._pools.items():
                close_tasks.append(pool.close())
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            self._pools.clear()
            logger.info("Closed all connection pools")
    
    async def health_check(self, connection_name: Optional[str] = None) -> Dict[str, HealthStatus]:
        """Perform health check on connections."""
        results = {}
        
        if connection_name:
            # Check specific connection
            connection = await self._registry.get_connection_by_name(connection_name)
            if connection:
                status = await self._health_checker.get_health_status(connection)
                results[connection_name] = status
        else:
            # Check all connections
            connections = await self._registry.list_connections(active_only=True)
            
            # Run health checks in parallel
            tasks = []
            for connection in connections:
                task = self._check_single_connection_health(connection)
                tasks.append(task)
            
            if tasks:
                health_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(health_results):
                    connection = connections[i]
                    if isinstance(result, Exception):
                        results[connection.connection_name] = HealthStatus.UNHEALTHY
                        logger.error(f"Health check failed for {connection.connection_name}: {result}")
                    else:
                        results[connection.connection_name] = result
        
        return results
    
    async def _check_single_connection_health(self, connection: DatabaseConnection) -> HealthStatus:
        """Check health of a single connection."""
        try:
            return await self._health_checker.get_health_status(connection)
        except Exception as e:
            logger.error(f"Health check error for {connection.connection_name}: {e}")
            return HealthStatus.UNHEALTHY
    
    async def get_pool_metrics(self, connection_name: str) -> Optional[PoolMetrics]:
        """Get metrics for a specific pool."""
        if connection_name in self._pools:
            return self._pools[connection_name].metrics
        return None
    
    async def get_all_pool_metrics(self) -> Dict[str, PoolMetrics]:
        """Get metrics for all pools."""
        metrics = {}
        for name, pool in self._pools.items():
            metrics[name] = pool.metrics
        return metrics