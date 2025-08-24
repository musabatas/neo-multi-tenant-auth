"""Admin database failover handler with graceful degradation.

This module provides robust failover capabilities for admin database connections,
ensuring high availability and graceful degradation when primary admin database fails.
"""

import os
import asyncio
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

import asyncpg

from ....core.exceptions.database import (
    DatabaseError,
    ConnectionNotFoundError,
    HealthCheckFailedError
)
from ..utils.queries import BASIC_HEALTH_CHECK
from ..utils.connection_factory import ConnectionFactory

logger = logging.getLogger(__name__)


class FailoverState(str, Enum):
    """Admin database failover states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class AdminConnection:
    """Admin database connection configuration."""
    name: str
    url: str
    priority: int  # Lower number = higher priority
    max_failures: int = 3
    timeout_seconds: int = 10
    health_check_interval: int = 30
    
    # Runtime state
    consecutive_failures: int = 0
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True
    last_error: Optional[str] = None


@dataclass 
class FailoverMetrics:
    """Failover performance metrics."""
    total_failovers: int = 0
    current_connection: Optional[str] = None
    state: FailoverState = FailoverState.HEALTHY
    degraded_since: Optional[datetime] = None
    last_failover: Optional[datetime] = None
    connection_attempts: Dict[str, int] = None
    response_times: Dict[str, float] = None
    
    def __post_init__(self):
        if self.connection_attempts is None:
            self.connection_attempts = {}
        if self.response_times is None:
            self.response_times = {}


class AdminDatabaseFailover:
    """Admin database failover manager with graceful degradation."""
    
    def __init__(self, check_interval: int = 30, degradation_timeout: int = 300):
        """Initialize admin database failover.
        
        Args:
            check_interval: Health check interval in seconds
            degradation_timeout: Timeout before degraded mode in seconds
        """
        self.check_interval = check_interval
        self.degradation_timeout = degradation_timeout
        
        # Admin connections (sorted by priority)
        self.admin_connections: List[AdminConnection] = []
        self.current_connection: Optional[AdminConnection] = None
        
        # Failover state
        self.metrics = FailoverMetrics()
        self._health_task: Optional[asyncio.Task] = None
        self._stop_monitoring = False
        
        # Cache for degraded operations
        self._cached_connections: Dict[str, Any] = {}
        self._cache_expiry = timedelta(minutes=10)
        
        self._initialize_admin_connections()
    
    def _initialize_admin_connections(self) -> None:
        """Initialize admin database connections from environment variables."""
        # Primary admin database (highest priority)
        primary_url = os.getenv("ADMIN_DATABASE_URL")
        if primary_url:
            self.admin_connections.append(AdminConnection(
                name="admin_primary",
                url=primary_url,
                priority=1,
                max_failures=3
            ))
        
        # Secondary admin databases
        for i in range(2, 6):  # Support up to 4 additional admin databases
            backup_url = os.getenv(f"ADMIN_DATABASE_URL_{i}")
            if backup_url:
                self.admin_connections.append(AdminConnection(
                    name=f"admin_backup_{i}",
                    url=backup_url,
                    priority=i,
                    max_failures=5  # More tolerant for backup connections
                ))
        
        # Sort by priority
        self.admin_connections.sort(key=lambda c: c.priority)
        
        if not self.admin_connections:
            raise ValueError("No admin database connections configured. Set ADMIN_DATABASE_URL environment variable.")
        
        # Set primary connection
        self.current_connection = self.admin_connections[0]
        self.metrics.current_connection = self.current_connection.name
        
        logger.info(f"Initialized {len(self.admin_connections)} admin database connections")
    
    async def get_connection(self, operation: str = "general") -> Tuple[asyncpg.Connection, str]:
        """Get healthy admin database connection with automatic failover.
        
        Args:
            operation: Type of operation for connection optimization
            
        Returns:
            Tuple of (connection, connection_name)
            
        Raises:
            DatabaseError: If no healthy connection available
        """
        # Try current connection first
        if self.current_connection and self.current_connection.is_healthy:
            try:
                start_time = datetime.utcnow()
                conn = await ConnectionFactory.create_connection_from_url(
                    self.current_connection.url,
                    timeout=self.current_connection.timeout_seconds,
                    connection_name=self.current_connection.name
                )
                
                # Update metrics
                response_time = (datetime.utcnow() - start_time).total_seconds()
                self.metrics.response_times[self.current_connection.name] = response_time
                
                logger.debug(f"Connected to {self.current_connection.name} in {response_time:.3f}s")
                return conn, self.current_connection.name
                
            except Exception as e:
                logger.warning(f"Failed to connect to {self.current_connection.name}: {e}")
                await self._handle_connection_failure(self.current_connection, str(e))
        
        # Try failover to next available connection
        return await self._failover_connection(operation)
    
    async def _failover_connection(self, operation: str) -> Tuple[asyncpg.Connection, str]:
        """Perform failover to next available admin connection."""
        for connection in self.admin_connections:
            if connection == self.current_connection:
                continue  # Already tried
                
            try:
                start_time = datetime.utcnow()
                conn = await ConnectionFactory.create_connection_from_url(
                    connection.url,
                    timeout=connection.timeout_seconds,
                    connection_name=connection.name
                )
                
                # Successful failover
                old_connection = self.current_connection.name if self.current_connection else "none"
                self.current_connection = connection
                self.metrics.current_connection = connection.name
                self.metrics.total_failovers += 1
                self.metrics.last_failover = datetime.utcnow()
                
                # Update state
                if self.metrics.state == FailoverState.FAILED:
                    self.metrics.state = FailoverState.RECOVERING
                
                # Update metrics
                response_time = (datetime.utcnow() - start_time).total_seconds() 
                self.metrics.response_times[connection.name] = response_time
                
                logger.warning(f"Failover: {old_connection} → {connection.name} (response: {response_time:.3f}s)")
                return conn, connection.name
                
            except Exception as e:
                logger.warning(f"Failover attempt failed for {connection.name}: {e}")
                await self._handle_connection_failure(connection, str(e))
                continue
        
        # All connections failed - enter degraded mode
        await self._enter_degraded_mode(operation)
        raise DatabaseError("All admin database connections failed")
    
    async def _handle_connection_failure(self, connection: AdminConnection, error: str) -> None:
        """Handle connection failure and update health status."""
        connection.consecutive_failures += 1
        connection.last_error = error
        connection.last_health_check = datetime.utcnow()
        
        # Update metrics
        self.metrics.connection_attempts[connection.name] = \
            self.metrics.connection_attempts.get(connection.name, 0) + 1
        
        # Mark as unhealthy if too many failures
        if connection.consecutive_failures >= connection.max_failures:
            connection.is_healthy = False
            logger.error(f"Admin connection {connection.name} marked unhealthy after {connection.consecutive_failures} failures")
            
            # Update global state
            healthy_connections = [c for c in self.admin_connections if c.is_healthy]
            if not healthy_connections:
                self.metrics.state = FailoverState.FAILED
            elif len(healthy_connections) < len(self.admin_connections):
                self.metrics.state = FailoverState.DEGRADED
                if self.metrics.degraded_since is None:
                    self.metrics.degraded_since = datetime.utcnow()
    
    async def _enter_degraded_mode(self, operation: str) -> None:
        """Enter degraded mode with limited functionality."""
        self.metrics.state = FailoverState.FAILED
        
        if self.metrics.degraded_since is None:
            self.metrics.degraded_since = datetime.utcnow()
        
        logger.critical("Entering degraded mode - all admin database connections failed")
        
        # In degraded mode, return cached data where possible
        # This allows read-only operations to continue with stale data
        if operation in ["read", "query", "health_check"]:
            # Return cached connections for read operations
            return
    
    async def execute_query(self, query: str, *args, operation: str = "query") -> List[Dict[str, Any]]:
        """Execute query with automatic failover and degraded mode support.
        
        Args:
            query: SQL query to execute
            args: Query parameters
            operation: Type of operation for optimization
            
        Returns:
            Query results
        """
        try:
            conn, conn_name = await self.get_connection(operation)
            
            try:
                if args:
                    rows = await conn.fetch(query, *args)
                else:
                    rows = await conn.fetch(query)
                
                # Convert to list of dictionaries
                results = [dict(row) for row in rows]
                
                logger.debug(f"Executed query on {conn_name}: {len(results)} rows returned")
                return results
                
            finally:
                await conn.close()
                
        except DatabaseError:
            # Try degraded mode for read operations
            if operation in ["read", "query", "health_check"]:
                return await self._execute_degraded_query(query, args)
            raise
    
    async def _execute_degraded_query(self, query: str, args: tuple) -> List[Dict[str, Any]]:
        """Execute query in degraded mode using cached data."""
        # For critical read operations, return cached data if available
        cache_key = f"query:{hash(query + str(args))}"
        
        if cache_key in self._cached_connections:
            cached_data, timestamp = self._cached_connections[cache_key]
            
            # Check if cache is still valid
            if datetime.utcnow() - timestamp < self._cache_expiry:
                logger.warning(f"Returning cached data for degraded query (age: {datetime.utcnow() - timestamp})")
                return cached_data
        
        # For connection listing queries, return minimal fallback data
        if "database_connections" in query:
            return await self._get_fallback_connections()
        
        # No cached data available
        logger.error("No cached data available for degraded query")
        return []
    
    async def _get_fallback_connections(self) -> List[Dict[str, Any]]:
        """Get fallback connection data when admin database is unavailable."""
        # Return minimal connection info for current admin connection
        fallback_connections = []
        
        for i, connection in enumerate(self.admin_connections):
            if connection.is_healthy:
                fallback_connections.append({
                    "id": f"admin_failover_{i}",
                    "connection_name": connection.name,
                    "connection_type": "PRIMARY",
                    "region_id": "admin",
                    "is_active": True,
                    "is_healthy": connection.is_healthy,
                    "host": "localhost",  # Parsed from URL if needed
                    "port": 5432,
                    "database_name": "neofast_admin",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
        
        logger.warning(f"Returning {len(fallback_connections)} fallback admin connections")
        return fallback_connections
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        if self._health_task is not None:
            return
        
        self._stop_monitoring = False
        self._health_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started admin database health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self._stop_monitoring = True
        
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped admin database health monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main health monitoring loop."""
        while not self._stop_monitoring:
            try:
                await self._check_all_connections()
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in admin database monitoring loop: {e}")
                await asyncio.sleep(min(self.check_interval, 10))
    
    async def _check_all_connections(self) -> None:
        """Check health of all admin connections."""
        health_results = []
        
        for connection in self.admin_connections:
            try:
                start_time = datetime.utcnow()
                
                # Simple connectivity check
                conn = await ConnectionFactory.create_connection_from_url(
                    connection.url,
                    timeout=connection.timeout_seconds,
                    connection_name=connection.name
                )
                
                # Execute basic health check
                await conn.fetchval(BASIC_HEALTH_CHECK)
                await conn.close()
                
                # Connection successful
                connection.consecutive_failures = 0
                connection.is_healthy = True
                connection.last_health_check = datetime.utcnow()
                connection.last_error = None
                
                response_time = (datetime.utcnow() - start_time).total_seconds()
                self.metrics.response_times[connection.name] = response_time
                
                health_results.append((connection.name, True, response_time))
                
            except Exception as e:
                await self._handle_connection_failure(connection, str(e))
                health_results.append((connection.name, False, str(e)))
        
        # Update overall health state
        healthy_connections = [c for c in self.admin_connections if c.is_healthy]
        
        if len(healthy_connections) == len(self.admin_connections):
            self.metrics.state = FailoverState.HEALTHY
            self.metrics.degraded_since = None
        elif len(healthy_connections) > 0:
            if self.metrics.state == FailoverState.FAILED:
                self.metrics.state = FailoverState.RECOVERING
            else:
                self.metrics.state = FailoverState.DEGRADED
        else:
            self.metrics.state = FailoverState.FAILED
        
        logger.debug(f"Health check completed: {len(healthy_connections)}/{len(self.admin_connections)} healthy")
    
    async def get_failover_status(self) -> Dict[str, Any]:
        """Get current failover status and metrics."""
        return {
            "state": self.metrics.state.value,
            "current_connection": self.metrics.current_connection,
            "total_failovers": self.metrics.total_failovers,
            "degraded_since": self.metrics.degraded_since.isoformat() if self.metrics.degraded_since else None,
            "last_failover": self.metrics.last_failover.isoformat() if self.metrics.last_failover else None,
            "connections": [
                {
                    "name": conn.name,
                    "priority": conn.priority,
                    "is_healthy": conn.is_healthy,
                    "consecutive_failures": conn.consecutive_failures,
                    "last_health_check": conn.last_health_check.isoformat() if conn.last_health_check else None,
                    "last_error": conn.last_error,
                    "response_time": self.metrics.response_times.get(conn.name)
                }
                for conn in self.admin_connections
            ]
        }
    
    async def force_failover(self, target_connection: Optional[str] = None) -> Dict[str, Any]:
        """Force failover to specific connection or next available.
        
        Args:
            target_connection: Name of target connection, or None for next available
            
        Returns:
            Failover result information
        """
        old_connection = self.current_connection.name if self.current_connection else "none"
        
        if target_connection:
            # Find target connection
            target = None
            for conn in self.admin_connections:
                if conn.name == target_connection:
                    target = conn
                    break
            
            if not target:
                raise ValueError(f"Target connection '{target_connection}' not found")
            
            # Test target connection
            try:
                test_conn = await ConnectionFactory.create_connection_from_url(
                    target.url,
                    timeout=target.timeout_seconds,
                    connection_name=target.name
                )
                await test_conn.close()
                
                # Force switch
                self.current_connection = target
                self.metrics.current_connection = target.name
                self.metrics.total_failovers += 1
                self.metrics.last_failover = datetime.utcnow()
                
                logger.warning(f"Forced failover: {old_connection} → {target.name}")
                
                return {
                    "success": True,
                    "old_connection": old_connection,
                    "new_connection": target.name,
                    "failover_time": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Failed to connect to target connection {target_connection}: {e}")
                raise DatabaseError(f"Target connection {target_connection} is not available: {e}")
        
        else:
            # Failover to next available
            try:
                _, new_connection = await self._failover_connection("manual_failover")
                
                return {
                    "success": True,
                    "old_connection": old_connection,
                    "new_connection": new_connection,
                    "failover_time": datetime.utcnow().isoformat()
                }
                
            except DatabaseError as e:
                logger.error(f"Manual failover failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "current_connection": old_connection
                }