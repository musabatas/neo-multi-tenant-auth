"""Database connection protocols for neo-commons."""

from abc import abstractmethod
from typing import Protocol, runtime_checkable, Optional, List, Dict, Any, AsyncContextManager
from contextlib import asynccontextmanager
import asyncpg

from .database_connection import DatabaseConnection
from ....core.value_objects.identifiers import DatabaseConnectionId, RegionId
from ....config.constants import ConnectionType, HealthStatus


@runtime_checkable
class ConnectionHealthChecker(Protocol):
    """Protocol for checking database connection health."""
    
    @abstractmethod
    async def check_health(self, connection: DatabaseConnection) -> bool:
        """Check if a database connection is healthy."""
        ...
    
    @abstractmethod
    async def get_health_status(self, connection: DatabaseConnection) -> HealthStatus:
        """Get detailed health status for a connection."""
        ...


@runtime_checkable
class ConnectionRegistry(Protocol):
    """Protocol for managing database connection registry."""
    
    @abstractmethod
    async def register_connection(self, connection: DatabaseConnection) -> None:
        """Register a new database connection."""
        ...
    
    @abstractmethod
    async def get_connection(self, connection_id: DatabaseConnectionId) -> Optional[DatabaseConnection]:
        """Get a connection by ID."""
        ...
    
    @abstractmethod
    async def get_connection_by_name(self, connection_name: str) -> Optional[DatabaseConnection]:
        """Get a connection by name."""
        ...
    
    @abstractmethod
    async def list_connections(self,
                              connection_type: Optional[ConnectionType] = None,
                              region_id: Optional[RegionId] = None,
                              active_only: bool = True) -> List[DatabaseConnection]:
        """List connections with optional filtering."""
        ...
    
    @abstractmethod
    async def update_connection(self, connection: DatabaseConnection) -> None:
        """Update an existing connection."""
        ...
    
    @abstractmethod
    async def remove_connection(self, connection_id: DatabaseConnectionId) -> None:
        """Remove a connection from the registry."""
        ...
    
    @abstractmethod
    async def get_healthy_connections(self, 
                                    connection_type: Optional[ConnectionType] = None,
                                    region_id: Optional[RegionId] = None) -> List[DatabaseConnection]:
        """Get all healthy connections."""
        ...


@runtime_checkable
class ConnectionPool(Protocol):
    """Protocol for database connection pooling."""
    
    @abstractmethod
    async def acquire_connection(self) -> asyncpg.Connection:
        """Acquire a connection from the pool."""
        ...
    
    @abstractmethod
    async def release_connection(self, connection: asyncpg.Connection) -> None:
        """Release a connection back to the pool."""
        ...
    
    @abstractmethod
    @asynccontextmanager
    async def connection(self) -> AsyncContextManager[asyncpg.Connection]:
        """Get a connection within a context manager."""
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Close the connection pool."""
        ...
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the pool is healthy."""
        ...
    
    @property
    @abstractmethod
    def size(self) -> int:
        """Get current pool size."""
        ...
    
    @property
    @abstractmethod
    def free_size(self) -> int:
        """Get number of free connections in pool."""
        ...


@runtime_checkable
class ConnectionManager(Protocol):
    """Protocol for managing database connections and pools."""
    
    @abstractmethod
    async def get_pool(self, connection_name: str) -> ConnectionPool:
        """Get or create a connection pool for the given connection."""
        ...
    
    @abstractmethod
    async def get_connection(self, connection_name: str) -> AsyncContextManager[asyncpg.Connection]:
        """Get a database connection from the pool."""
        ...
    
    @abstractmethod
    async def execute_query(self, 
                           connection_name: str, 
                           query: str, 
                           *args: Any) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        ...
    
    @abstractmethod
    async def execute_fetchrow(self, 
                              connection_name: str, 
                              query: str, 
                              *args: Any) -> Optional[Dict[str, Any]]:
        """Execute a query and return single row."""
        ...
    
    @abstractmethod
    async def execute_fetchval(self, 
                              connection_name: str, 
                              query: str, 
                              *args: Any) -> Any:
        """Execute a query and return single value."""
        ...
    
    @abstractmethod
    async def execute_command(self, 
                             connection_name: str, 
                             command: str, 
                             *args: Any) -> str:
        """Execute a command (INSERT, UPDATE, DELETE) and return status."""
        ...
    
    @abstractmethod
    async def close_pool(self, connection_name: str) -> None:
        """Close a specific connection pool."""
        ...
    
    @abstractmethod
    async def close_all_pools(self) -> None:
        """Close all connection pools."""
        ...
    
    @abstractmethod
    async def health_check(self, connection_name: Optional[str] = None) -> Dict[str, HealthStatus]:
        """Perform health check on connections."""
        ...


@runtime_checkable
class SchemaResolver(Protocol):
    """Protocol for resolving database schemas based on context."""
    
    @abstractmethod
    async def resolve_schema(self, 
                           tenant_id: Optional[str] = None,
                           context_type: str = "admin") -> str:
        """Resolve the correct schema name based on context."""
        ...
    
    @abstractmethod
    async def get_tenant_schema(self, tenant_id: str) -> str:
        """Get the specific schema name for a tenant."""
        ...
    
    @abstractmethod
    async def validate_schema_name(self, schema_name: str) -> bool:
        """Validate that a schema name is safe to use."""
        ...
    
    @abstractmethod
    async def get_admin_schema(self) -> str:
        """Get the admin schema name."""
        ...
    
    @abstractmethod
    async def get_platform_schema(self) -> str:
        """Get the platform common schema name."""
        ...


@runtime_checkable
class FailoverManager(Protocol):
    """Protocol for handling database failover."""
    
    @abstractmethod
    async def get_primary_connection(self, connection_type: ConnectionType) -> Optional[DatabaseConnection]:
        """Get the primary connection for a given type."""
        ...
    
    @abstractmethod
    async def get_replica_connections(self, connection_type: ConnectionType) -> List[DatabaseConnection]:
        """Get replica connections for a given type."""
        ...
    
    @abstractmethod
    async def initiate_failover(self, 
                               failed_connection: DatabaseConnection,
                               reason: str) -> Optional[DatabaseConnection]:
        """Initiate failover to a healthy connection."""
        ...
    
    @abstractmethod
    async def notify_connection_failure(self, connection: DatabaseConnection, error: Exception) -> None:
        """Notify about a connection failure."""
        ...
    
    @abstractmethod
    async def can_failover(self, connection: DatabaseConnection) -> bool:
        """Check if failover is possible for a connection."""
        ...


@runtime_checkable
class ConnectionLoadBalancer(Protocol):
    """Protocol for load balancing across database connections."""
    
    @abstractmethod
    async def get_best_connection(self, 
                                 connection_type: ConnectionType,
                                 region_id: Optional[RegionId] = None,
                                 read_only: bool = False) -> Optional[DatabaseConnection]:
        """Get the best available connection based on load balancing strategy."""
        ...
    
    @abstractmethod
    async def update_connection_metrics(self, 
                                       connection: DatabaseConnection,
                                       response_time_ms: float,
                                       error: Optional[Exception] = None) -> None:
        """Update connection performance metrics."""
        ...
    
    @abstractmethod
    async def get_connection_load(self, connection: DatabaseConnection) -> float:
        """Get current load metric for a connection (0.0 to 1.0)."""
        ...


@runtime_checkable
class DatabaseRepository(Protocol):
    """Base protocol for database repositories."""
    
    @abstractmethod
    async def execute_query(self, 
                           query: str, 
                           *args: Any,
                           schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute a query in the specified schema."""
        ...
    
    @abstractmethod
    async def execute_fetchrow(self, 
                              query: str, 
                              *args: Any,
                              schema_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Execute a query and return single row."""
        ...
    
    @abstractmethod
    async def execute_fetchval(self, 
                              query: str, 
                              *args: Any,
                              schema_name: Optional[str] = None) -> Any:
        """Execute a query and return single value."""
        ...
    
    @abstractmethod
    async def execute_command(self, 
                             command: str, 
                             *args: Any,
                             schema_name: Optional[str] = None) -> str:
        """Execute a command and return status."""
        ...


@runtime_checkable
class DatabaseConnectionRepository(Protocol):
    """Protocol for database connection management repository."""
    
    @abstractmethod
    async def create_connection(self, connection: DatabaseConnection) -> DatabaseConnection:
        """Create a new database connection record."""
        ...
    
    @abstractmethod
    async def get_connection_by_id(self, connection_id: DatabaseConnectionId) -> Optional[DatabaseConnection]:
        """Get connection by ID."""
        ...
    
    @abstractmethod
    async def get_connection_by_name(self, connection_name: str) -> Optional[DatabaseConnection]:
        """Get connection by name."""
        ...
    
    @abstractmethod
    async def list_connections(self,
                              connection_type: Optional[ConnectionType] = None,
                              region_id: Optional[RegionId] = None,
                              active_only: bool = True) -> List[DatabaseConnection]:
        """List connections with filtering."""
        ...
    
    @abstractmethod
    async def update_connection(self, connection: DatabaseConnection) -> DatabaseConnection:
        """Update existing connection."""
        ...
    
    @abstractmethod
    async def update_health_status(self, 
                                  connection_id: DatabaseConnectionId,
                                  is_healthy: bool,
                                  consecutive_failures: int = 0) -> None:
        """Update connection health status."""
        ...
    
    @abstractmethod
    async def soft_delete_connection(self, connection_id: DatabaseConnectionId, reason: str) -> None:
        """Soft delete a connection."""
        ...
    
    @abstractmethod
    async def get_healthy_connections(self, 
                                    connection_type: Optional[ConnectionType] = None,
                                    region_id: Optional[RegionId] = None) -> List[DatabaseConnection]:
        """Get all healthy connections."""
        ...