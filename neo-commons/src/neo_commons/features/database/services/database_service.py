"""Database feature service that orchestrates all database functionality.

This service provides a high-level interface to the database infrastructure,
coordinating connection management, schema resolution, health monitoring,
and query execution.
"""

import logging
from typing import Dict, List, Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager

from ..entities import (
    ConnectionManager,
    ConnectionPool,
    SchemaResolver,
    ConnectionHealthChecker as HealthChecker,
    ConnectionRegistry,
    DatabaseConnection
)
from ....core.value_objects import TenantId
from ....core.shared.context import RequestContext
from ....core.exceptions import (
    DatabaseError,
    ConnectionNotFoundError,
    SchemaError,
    HealthCheckFailedError
)
from ..repositories import (
    DatabaseConnectionManager,
    AsyncConnectionPool,
    InMemoryConnectionRegistry,
    DatabaseHealthChecker,
    ContinuousHealthMonitor,
    DatabaseSchemaResolver
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """High-level database service orchestrating all database functionality."""
    
    def __init__(self,
                 connection_manager: ConnectionManager,
                 schema_resolver: SchemaResolver,
                 health_checker: HealthChecker,
                 connection_registry: ConnectionRegistry):
        self.connection_manager = connection_manager
        self.schema_resolver = schema_resolver
        self.health_checker = health_checker
        self.connection_registry = connection_registry
        
        # Service state
        self._initialized = False
        self._health_monitor: Optional[ContinuousHealthMonitor] = None
    
    async def initialize(self) -> None:
        """Initialize the database service."""
        if self._initialized:
            return
        
        try:
            # Initialize connection registry
            await self.connection_registry.initialize()
            
            # Start health monitoring
            self._health_monitor = ContinuousHealthMonitor(
                self.health_checker,
                self.connection_registry
            )
            await self._health_monitor.start_monitoring()
            
            self._initialized = True
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database service: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the database service."""
        if not self._initialized:
            return
        
        try:
            # Stop health monitoring
            if self._health_monitor:
                await self._health_monitor.stop_monitoring()
            
            # Close all connections
            await self.connection_manager.close_all()
            
            self._initialized = False
            logger.info("Database service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during database service shutdown: {e}")
    
    async def get_connection_pool(self, connection_name: str) -> ConnectionPool:
        """Get connection pool by name."""
        try:
            return await self.connection_manager.get_pool(connection_name)
        except Exception as e:
            raise ConnectionNotFoundError(f"Connection pool not found: {connection_name}: {e}")
    
    async def get_tenant_connection_pool(self, tenant_id: str) -> ConnectionPool:
        """Get connection pool for a specific tenant."""
        try:
            # Resolve tenant schema and connection
            schema_info = await self.schema_resolver.resolve_tenant_schema(tenant_id)
            connection_name = schema_info.connection_name
            
            return await self.get_connection_pool(connection_name)
        except Exception as e:
            raise ConnectionNotFoundError(f"Tenant connection not found: {tenant_id}: {e}")
    
    @asynccontextmanager
    async def get_connection(self, connection_name: str):
        """Get database connection with automatic cleanup."""
        pool = await self.get_connection_pool(connection_name)
        async with pool.connection() as connection:
            yield connection
    
    @asynccontextmanager 
    async def get_tenant_connection(self, tenant_id: str):
        """Get tenant-specific database connection."""
        pool = await self.get_tenant_connection_pool(tenant_id)
        async with pool.connection() as connection:
            # Set the correct schema for the connection
            schema_info = await self.schema_resolver.resolve_tenant_schema(tenant_id)
            if schema_info.schema_name:
                await connection.execute(f"SET search_path TO {schema_info.schema_name}")
            yield connection
    
    async def execute_query(self,
                           connection_name: str,
                           query: str,
                           *args,
                           **kwargs) -> Any:
        """Execute a query on a specific connection."""
        async with self.get_connection(connection_name) as conn:
            return await conn.fetch(query, *args, **kwargs)
    
    async def execute_tenant_query(self,
                                  tenant_id: str,
                                  query: str,
                                  *args,
                                  **kwargs) -> Any:
        """Execute a query for a specific tenant."""
        async with self.get_tenant_connection(tenant_id) as conn:
            return await conn.fetch(query, *args, **kwargs)
    
    @asynccontextmanager
    async def transaction(self, connection_name: str):
        """Start a database transaction."""
        async with self.get_connection(connection_name) as conn:
            async with conn.transaction():
                yield conn
    
    @asynccontextmanager
    async def tenant_transaction(self, tenant_id: str):
        """Start a tenant-specific database transaction."""
        async with self.get_tenant_connection(tenant_id) as conn:
            async with conn.transaction():
                yield conn
    
    async def health_check(self) -> Dict[str, Any]:
        """Get comprehensive health status of all database connections."""
        try:
            connections = await self.connection_registry.get_all_connections()
            health_results = {}
            
            for connection in connections:
                try:
                    is_healthy = await self.health_checker.check_health(connection)
                    health_results[connection.connection_name] = {
                        "healthy": is_healthy,
                        "connection_active": connection.is_active,
                        "error_message": None if is_healthy else "Health check failed"
                    }
                except Exception as e:
                    health_results[connection.connection_name] = {
                        "healthy": False,
                        "error_message": str(e)
                    }
            
            return {
                "overall_healthy": all(result["healthy"] for result in health_results.values()),
                "connections": health_results,
                "total_connections": len(connections)
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "overall_healthy": False,
                "error": str(e)
            }
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics for all database connections."""
        try:
            stats = {}
            connections = await self.connection_registry.get_all_connections()
            
            for connection in connections:
                try:
                    pool = await self.connection_manager.get_pool(connection.connection_name)
                    pool_stats = await pool.get_stats()
                    stats[connection.connection_name] = pool_stats
                except Exception as e:
                    stats[connection.connection_name] = {"error": str(e)}
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {"error": str(e)}
    
    async def resolve_tenant_schema(self, tenant_id: str) -> Dict[str, Any]:
        """Resolve schema information for a tenant."""
        try:
            schema_info = await self.schema_resolver.resolve_tenant_schema(tenant_id)
            return {
                "tenant_id": tenant_id,
                "schema_name": schema_info.schema_name,
                "connection_name": schema_info.connection_name,
                "region": schema_info.region,
                "database_name": schema_info.database_name
            }
        except Exception as e:
            logger.error(f"Failed to resolve tenant schema: {e}")
            raise SchemaError(f"Could not resolve schema for tenant {tenant_id}: {e}")


class DatabaseManager:
    """Singleton manager for database service."""
    
    _instance: Optional[DatabaseService] = None
    
    @classmethod
    async def get_instance(cls) -> DatabaseService:
        """Get singleton database service instance."""
        if cls._instance is None:
            # Create infrastructure components
            connection_registry = InMemoryConnectionRegistry()
            health_checker = DatabaseHealthChecker()
            connection_manager = DatabaseConnectionManager(
                registry=connection_registry,
                health_checker=health_checker
            )
            schema_resolver = DatabaseSchemaResolver(connection_registry)
            
            # Initialize admin database connection from environment
            await cls._initialize_admin_connection(connection_registry)
            
            # Auto-load all database connections from admin.database_connections table
            await cls._auto_load_database_connections(connection_registry)
            
            # Create service
            cls._instance = DatabaseService(
                connection_manager=connection_manager,
                schema_resolver=schema_resolver,
                health_checker=health_checker,
                connection_registry=connection_registry
            )
            
            # Initialize service
            await cls._instance.initialize()
        
        return cls._instance
    
    @classmethod
    async def _initialize_admin_connection(cls, registry) -> None:
        """Initialize admin database connection from environment variables."""
        import os
        from ..entities.database_connection import DatabaseConnection
        
        # Get admin database URL from environment
        admin_db_url = os.getenv("ADMIN_DATABASE_URL")
        if not admin_db_url:
            raise ValueError("ADMIN_DATABASE_URL environment variable is required")
        
        try:
            # Create admin database connection from URL
            admin_connection = DatabaseConnection.from_url(
                connection_name="admin",
                database_url=admin_db_url,
                region_id="admin"
            )
            
            # Register the admin connection
            await registry.register_connection(admin_connection)
            
            logger.info(f"Initialized admin database connection: {admin_connection.safe_dsn}")
            
        except Exception as e:
            logger.error(f"Failed to initialize admin database connection: {e}")
            raise
    
    @classmethod
    async def _auto_load_database_connections(cls, registry) -> None:
        """Auto-load all database connections from admin.database_connections table."""
        try:
            # Import here to avoid circular imports
            import os
            import asyncpg
            from ....utils.encryption import decrypt_password, is_encrypted
            from ..entities.database_connection import DatabaseConnection, ConnectionType
            from ....core.value_objects import DatabaseConnectionId, RegionId
            from ....utils.uuid import generate_uuid7
            from datetime import datetime, timezone
            
            # Get admin database URL to load other connections
            admin_db_url = os.getenv("ADMIN_DATABASE_URL")
            if not admin_db_url:
                logger.warning("ADMIN_DATABASE_URL not available for auto-loading connections")
                return
            
            # Connect to admin database to load connections
            conn = await asyncpg.connect(admin_db_url)
            
            try:
                # Query all active database connections except admin (already loaded)
                query = """
                    SELECT 
                        id, region_id, connection_name, connection_type,
                        host, port, database_name, ssl_mode, username, encrypted_password,
                        pool_min_size, pool_max_size, pool_timeout_seconds, pool_recycle_seconds, pool_pre_ping,
                        is_active, is_healthy, last_health_check, consecutive_failures, max_consecutive_failures,
                        metadata, tags, created_at, updated_at
                    FROM admin.database_connections 
                    WHERE deleted_at IS NULL AND is_active = true AND connection_name != 'admin'
                    ORDER BY connection_name
                """
                
                rows = await conn.fetch(query)
                loaded_count = 0
                
                for row in rows:
                    try:
                        # Map string connection type to enum
                        connection_type_mapping = {
                            "primary": ConnectionType.PRIMARY,
                            "replica": ConnectionType.REPLICA,
                            "analytics": ConnectionType.ANALYTICS,
                            "backup": ConnectionType.BACKUP
                        }
                        
                        connection_type = connection_type_mapping.get(
                            row["connection_type"], 
                            ConnectionType.PRIMARY
                        )
                        
                        # Decrypt password if it's encrypted
                        password = row["encrypted_password"] or ""
                        if password and is_encrypted(password):
                            try:
                                password = decrypt_password(password)
                            except Exception as decrypt_error:
                                logger.error(f"Failed to decrypt password for connection {row['connection_name']}: {decrypt_error}")
                                # Keep encrypted password - connection will fail health checks but will be registered
                        
                        # Create DatabaseConnection entity
                        connection = DatabaseConnection(
                            id=DatabaseConnectionId(str(row["id"])),
                            region_id=RegionId(str(row["region_id"])),
                            connection_name=row["connection_name"],
                            connection_type=connection_type,
                            host=row["host"],
                            port=row["port"] or 5432,
                            database_name=row["database_name"],
                            ssl_mode=row["ssl_mode"] or "prefer",
                            username=row["username"] or "postgres",
                            encrypted_password=password,
                            pool_min_size=row["pool_min_size"] or 5,
                            pool_max_size=row["pool_max_size"] or 20,
                            pool_timeout_seconds=row["pool_timeout_seconds"] or 30,
                            pool_recycle_seconds=row["pool_recycle_seconds"] or 3600,
                            pool_pre_ping=row["pool_pre_ping"] if row["pool_pre_ping"] is not None else True,
                            is_active=row["is_active"] if row["is_active"] is not None else True,
                            is_healthy=row["is_healthy"] if row["is_healthy"] is not None else True,
                            last_health_check=row["last_health_check"],
                            consecutive_failures=row["consecutive_failures"] or 0,
                            max_consecutive_failures=row["max_consecutive_failures"] or 3,
                            metadata=row["metadata"] or {},
                            tags=row["tags"] or [],
                            created_at=row["created_at"] or datetime.now(timezone.utc),
                            updated_at=row["updated_at"] or datetime.now(timezone.utc),
                            deleted_at=row.get("deleted_at")
                        )
                        
                        # Register the connection
                        await registry.register_connection(connection)
                        loaded_count += 1
                        logger.debug(f"Auto-loaded database connection: {connection.connection_name}")
                        
                    except Exception as connection_error:
                        logger.error(f"Failed to load database connection {row.get('connection_name', 'unknown')}: {connection_error}")
                        continue
                
                logger.info(f"Auto-loaded {loaded_count} database connections from admin.database_connections table")
                
            finally:
                await conn.close()
                
        except Exception as e:
            # Log error but don't fail startup - admin connection should still work
            logger.error(f"Failed to auto-load database connections: {e}")
    
    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown the database service."""
        if cls._instance:
            await cls._instance.shutdown()
            cls._instance = None


# Convenience functions for easy access
async def get_database_service() -> DatabaseService:
    """Get database service instance."""
    return await DatabaseManager.get_instance()


async def get_connection_pool(connection_name: str) -> ConnectionPool:
    """Get connection pool by name."""
    service = await get_database_service()
    return await service.get_connection_pool(connection_name)


async def get_tenant_connection_pool(tenant_id: str) -> ConnectionPool:
    """Get connection pool for tenant."""
    service = await get_database_service()
    return await service.get_tenant_connection_pool(tenant_id)