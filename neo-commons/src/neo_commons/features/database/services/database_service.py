"""Database feature service that orchestrates all database functionality.

This service provides a high-level interface to the database infrastructure,
coordinating connection management, schema resolution, health monitoring,
and query execution.
"""

import logging
from typing import Dict, List, Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager

from ....infrastructure.monitoring import critical_performance, medium_performance

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
    RedisConnectionRegistry,
    DatabaseHealthChecker,
    ContinuousHealthMonitor,
    DatabaseSchemaResolver,
    AdminDatabaseFailover,
    ConnectionPoolOptimizer
)
from ..utils.connection_factory import ConnectionFactory
from ..utils.queries import CONNECTION_REGISTRY_LOAD, CONNECTION_REGISTRY_BY_NAME, CONNECTION_REGISTRY_LOAD_NON_ADMIN

logger = logging.getLogger(__name__)


class DatabaseService:
    """High-level database service orchestrating all database functionality."""
    
    def __init__(self,
                 connection_manager: ConnectionManager,
                 schema_resolver: SchemaResolver,
                 health_checker: HealthChecker,
                 connection_registry: ConnectionRegistry,
                 admin_failover: Optional[AdminDatabaseFailover] = None,
                 pool_optimizer: Optional[ConnectionPoolOptimizer] = None):
        self.connection_manager = connection_manager
        self.schema_resolver = schema_resolver
        self.health_checker = health_checker
        self.connection_registry = connection_registry
        self.admin_failover = admin_failover
        self.pool_optimizer = pool_optimizer
        
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
            
            # Start admin database failover monitoring
            if self.admin_failover:
                await self.admin_failover.start_monitoring()
                logger.info("Started admin database failover monitoring")
            
            # Start health monitoring
            self._health_monitor = ContinuousHealthMonitor(
                self.health_checker,
                self.connection_registry
            )
            await self._health_monitor.start_monitoring()
            
            # Start pool optimization
            if self.pool_optimizer:
                await self.pool_optimizer.start_optimization()
                logger.info("Started connection pool optimization")
            
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
            
            # Stop pool optimization
            if self.pool_optimizer:
                await self.pool_optimizer.stop_optimization()
                logger.info("Stopped connection pool optimization")
            
            # Stop admin database failover monitoring
            if self.admin_failover:
                await self.admin_failover.stop_monitoring()
                logger.info("Stopped admin database failover monitoring")
            
            # Close all connections
            await self.connection_manager.close_all()
            
            self._initialized = False
            logger.info("Database service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during database service shutdown: {e}")
    
    @critical_performance(name="database.get_connection_pool", include_args=True)
    async def get_connection_pool(self, connection_name: str) -> ConnectionPool:
        """Get connection pool by name."""
        try:
            return await self.connection_manager.get_pool(connection_name)
        except Exception as e:
            raise ConnectionNotFoundError(f"Connection pool not found: {connection_name}: {e}")
    
    @critical_performance(name="database.get_tenant_connection_pool", include_args=True)
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
    @critical_performance(name="database.get_connection", include_args=True)
    async def get_connection(self, connection_name: str):
        """Get database connection with automatic cleanup."""
        pool = await self.get_connection_pool(connection_name)
        async with pool.connection() as connection:
            yield connection
    
    @asynccontextmanager 
    @critical_performance(name="database.get_tenant_connection", include_args=True)
    async def get_tenant_connection(self, tenant_id: str):
        """Get tenant-specific database connection."""
        pool = await self.get_tenant_connection_pool(tenant_id)
        async with pool.connection() as connection:
            # Set the correct schema for the connection
            schema_info = await self.schema_resolver.resolve_tenant_schema(tenant_id)
            if schema_info.schema_name:
                await connection.execute(f"SET search_path TO {schema_info.schema_name}")
            yield connection
    
    @critical_performance(name="database.execute_query", include_args=True)
    async def execute_query(self,
                           connection_name: str,
                           query: str,
                           *args,
                           **kwargs) -> Any:
        """Execute a query on a specific connection."""
        async with self.get_connection(connection_name) as conn:
            return await conn.fetch(query, *args, **kwargs)
    
    @critical_performance(name="database.execute_tenant_query", include_args=True)
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
    
    @medium_performance(name="database.health_check")
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
    
    @medium_performance(name="database.resolve_tenant_schema", include_args=True)
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
    
    async def get_admin_failover_status(self) -> Dict[str, Any]:
        """Get admin database failover status and metrics."""
        if not self.admin_failover:
            return {"error": "Admin failover not configured"}
        
        try:
            return await self.admin_failover.get_failover_status()
        except Exception as e:
            logger.error(f"Failed to get admin failover status: {e}")
            return {"error": str(e)}
    
    async def force_admin_failover(self, target_connection: Optional[str] = None) -> Dict[str, Any]:
        """Force admin database failover to specific or next connection."""
        if not self.admin_failover:
            return {"success": False, "error": "Admin failover not configured"}
        
        try:
            return await self.admin_failover.force_failover(target_connection)
        except Exception as e:
            logger.error(f"Failed to force admin failover: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_pool_optimization_report(self) -> Dict[str, Any]:
        """Get pool optimization report and statistics."""
        if not self.pool_optimizer:
            return {"error": "Pool optimization not configured"}
        
        try:
            return await self.pool_optimizer.get_optimization_report()
        except Exception as e:
            logger.error(f"Failed to get pool optimization report: {e}")
            return {"error": str(e)}
    
    async def force_pool_optimization(self, connection_name: Optional[str] = None) -> Dict[str, Any]:
        """Force immediate pool optimization for specific or all connections."""
        if not self.pool_optimizer:
            return {"success": False, "error": "Pool optimization not configured"}
        
        try:
            decisions = await self.pool_optimizer.force_optimization(connection_name)
            return {
                "success": True,
                "optimizations_applied": len(decisions),
                "decisions": [
                    {
                        "connection": d.connection_name,
                        "old_size": d.current_pool_size,
                        "new_size": d.recommended_pool_size,
                        "confidence": d.confidence,
                        "reasoning": d.reasoning,
                        "cost_impact": d.estimated_cost_impact
                    }
                    for d in decisions
                ]
            }
        except Exception as e:
            logger.error(f"Failed to force pool optimization: {e}")
            return {"success": False, "error": str(e)}


class DatabaseManager:
    """Database service factory with singleton support and dependency injection."""
    
    _instance: Optional[DatabaseService] = None
    
    @classmethod
    async def create_registry(cls, 
                            registry_type: str = "memory",
                            cache_instance: Optional[Any] = None,
                            redis_key_prefix: str = "neo:db:connections") -> ConnectionRegistry:
        """Create connection registry based on type.
        
        Args:
            registry_type: Type of registry ('memory' or 'redis')
            cache_instance: Redis cache instance for distributed registry
            redis_key_prefix: Key prefix for Redis keys
            
        Returns:
            Configured ConnectionRegistry instance
        """
        if registry_type.lower() == "redis":
            if cache_instance is None:
                # Import cache service to create Redis instance
                try:
                    from ...cache.services.cache_service import CacheService
                    cache_service = CacheService()
                    cache_instance = await cache_service.get_cache("redis")
                    
                    if cache_instance is None:
                        logger.warning("Redis cache not available, falling back to in-memory registry")
                        return InMemoryConnectionRegistry()
                        
                except Exception as e:
                    logger.warning(f"Failed to create Redis cache, falling back to in-memory registry: {e}")
                    return InMemoryConnectionRegistry()
            
            registry = RedisConnectionRegistry(
                cache=cache_instance,
                key_prefix=redis_key_prefix
            )
            logger.info("Created Redis connection registry for distributed deployments")
            return registry
            
        else:
            # Default to in-memory registry
            registry = InMemoryConnectionRegistry()
            logger.info("Created in-memory connection registry")
            return registry
    
    @classmethod
    async def create_service(cls,
                           connection_manager: Optional[ConnectionManager] = None,
                           schema_resolver: Optional[SchemaResolver] = None,
                           health_checker: Optional[HealthChecker] = None,
                           connection_registry: Optional[ConnectionRegistry] = None,
                           registry_type: str = "memory",
                           redis_cache: Optional[Any] = None) -> DatabaseService:
        """Create a DatabaseService with dependency injection support.
        
        This method allows for custom implementations of each component,
        enabling better testing and flexibility compared to the singleton pattern.
        
        Args:
            connection_manager: Custom connection manager implementation
            schema_resolver: Custom schema resolver implementation  
            health_checker: Custom health checker implementation
            connection_registry: Custom connection registry implementation
            registry_type: Type of registry ('memory' or 'redis') if connection_registry not provided
            redis_cache: Redis cache instance for distributed registry
            
        Returns:
            Configured DatabaseService instance
        """
        # Use provided components or create defaults
        if connection_registry is None:
            connection_registry = await cls.create_registry(
                registry_type=registry_type,
                cache_instance=redis_cache
            )
            
        if health_checker is None:
            health_checker = DatabaseHealthChecker()
            
        if connection_manager is None:
            connection_manager = DatabaseConnectionManager(
                registry=connection_registry,
                health_checker=health_checker
            )
            
        if schema_resolver is None:
            schema_resolver = DatabaseSchemaResolver(connection_manager=connection_manager)
        
        # Create admin database failover handler
        admin_failover = AdminDatabaseFailover()
        
        # Create pool optimizer
        pool_optimizer = ConnectionPoolOptimizer(
            connection_manager=connection_manager,
            connection_registry=connection_registry,
            optimization_interval=300  # 5 minutes
        )
        
        # Auto-load database connections using failover-aware method
        await cls._auto_load_database_connections_with_failover(connection_registry, admin_failover)
        
        # Create and return service instance
        service = DatabaseService(
            connection_manager=connection_manager,
            schema_resolver=schema_resolver,
            health_checker=health_checker,
            connection_registry=connection_registry,
            admin_failover=admin_failover,
            pool_optimizer=pool_optimizer
        )
        
        logger.info("DatabaseService created with dependency injection")
        return service
    
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
            conn = await ConnectionFactory.create_connection_from_url(
                admin_db_url, 
                connection_name="admin_auto_load"
            )
            
            try:
                # Query all active database connections except admin (already loaded)
                query = CONNECTION_REGISTRY_LOAD_NON_ADMIN
                
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
                            last_health_check=row.get("last_health_check"),
                            consecutive_failures=row.get("consecutive_failures") or 0,
                            max_consecutive_failures=row.get("max_consecutive_failures") or 3,
                            metadata=row.get("metadata") or {},
                            tags=row.get("tags") or [],
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
    async def _auto_load_database_connections_with_failover(cls, registry, admin_failover: AdminDatabaseFailover) -> None:
        """Auto-load database connections using admin failover for high availability."""
        try:
            # Import here to avoid circular imports
            from ....utils.encryption import decrypt_password, is_encrypted
            from ..entities.database_connection import DatabaseConnection, ConnectionType
            from ....core.value_objects import DatabaseConnectionId, RegionId
            from ....utils.uuid import generate_uuid7
            from datetime import datetime, timezone
            
            loaded_count = 0
            
            # Load other database connections from admin database with failover support
            query = """
                SELECT 
                    id, region_id, connection_name, connection_type,
                    host, port, database_name, ssl_mode, username, encrypted_password,
                    connection_options, pool_min_size, pool_max_size, 
                    pool_timeout_seconds, pool_recycle_seconds, pool_pre_ping,
                    is_active, is_healthy, consecutive_failures, max_consecutive_failures,
                    metadata, tags, created_at, updated_at, last_health_check, deleted_at
                FROM admin.database_connections
                WHERE is_active = true
                ORDER BY connection_name
            """
            
            # Use admin failover to execute query with automatic failover
            rows = await admin_failover.execute_query(query, operation="read")
            
            for row in rows:
                try:
                    # Convert row dict to expected format
                    row_data = row  # Already a dict from failover handler
                    
                    # Skip admin connection - it's handled by failover system
                    if row_data["connection_name"] == "admin":
                        continue
                    
                    # Decrypt password if encrypted
                    password = row_data["encrypted_password"]
                    if password and is_encrypted(password):
                        password = decrypt_password(password)
                    
                    # Create connection object
                    connection = DatabaseConnection(
                        id=DatabaseConnectionId(row_data["id"]) if row_data["id"] else DatabaseConnectionId(generate_uuid7()),
                        connection_name=row_data["connection_name"],
                        host=row_data["host"],
                        port=row_data["port"] or 5432,
                        database_name=row_data["database_name"],
                        username=row_data["username"],
                        encrypted_password=password,
                        ssl_mode=row_data["ssl_mode"] or "prefer",
                        connection_type=ConnectionType(row_data["connection_type"]),
                        region_id=RegionId(row_data["region_id"]),
                        connection_options=row_data["connection_options"] or {},
                        pool_min_size=row_data["pool_min_size"] or 5,
                        pool_max_size=row_data["pool_max_size"] or 20,
                        pool_timeout_seconds=row_data["pool_timeout_seconds"] or 30,
                        pool_recycle_seconds=row_data["pool_recycle_seconds"] or 3600,
                        pool_pre_ping=row_data["pool_pre_ping"] if row_data["pool_pre_ping"] is not None else True,
                        is_active=row_data["is_active"] if row_data["is_active"] is not None else True,
                        is_healthy=row_data["is_healthy"] if row_data["is_healthy"] is not None else True,
                        last_health_check=row_data["last_health_check"],
                        consecutive_failures=row_data["consecutive_failures"] or 0,
                        max_consecutive_failures=row_data["max_consecutive_failures"] or 3,
                        metadata=row_data["metadata"] or {},
                        tags=row_data["tags"] or [],
                        created_at=row_data["created_at"] or datetime.now(timezone.utc),
                        updated_at=row_data["updated_at"] or datetime.now(timezone.utc),
                        deleted_at=row_data.get("deleted_at")
                    )
                    
                    # Register the connection
                    await registry.register_connection(connection)
                    loaded_count += 1
                    logger.debug(f"Auto-loaded database connection: {connection.connection_name}")
                    
                except Exception as connection_error:
                    logger.error(f"Failed to load database connection {row.get('connection_name', 'unknown')}: {connection_error}")
                    continue
            
            logger.info(f"Auto-loaded {loaded_count} database connections from admin.database_connections table with failover support")
            
        except Exception as e:
            # Log error but don't fail startup - failover system should handle degraded mode
            logger.error(f"Failed to auto-load database connections with failover: {e}")
            logger.warning("System will continue with degraded functionality")
    
    @classmethod
    async def sync_redis_registry(cls, redis_registry: RedisConnectionRegistry) -> Dict[str, Any]:
        """Synchronize Redis registry with database connections.
        
        This method loads all database connections and syncs them to Redis registry.
        Useful for initializing or refreshing distributed registry state.
        
        Args:
            redis_registry: Redis connection registry to sync
            
        Returns:
            Sync statistics including counts and errors
        """
        try:
            logger.info("Starting Redis registry synchronization...")
            
            sync_stats = {
                "connections_synced": 0,
                "connections_failed": 0,
                "errors": []
            }
            
            # Load all database connections from admin database
            database_connections = []
            
            # Import here to avoid circular imports
            import os
            import asyncpg
            from ....utils.encryption import decrypt_password, is_encrypted
            from ..entities.database_connection import DatabaseConnection, ConnectionType
            from ....core.value_objects import DatabaseConnectionId, RegionId
            from ....utils.uuid import generate_uuid7
            from datetime import datetime, timezone
            
            # Get admin database URL
            admin_db_url = os.getenv("ADMIN_DATABASE_URL")
            if not admin_db_url:
                raise ValueError("ADMIN_DATABASE_URL environment variable is required for Redis sync")
            
            # Add admin connection first
            admin_connection = DatabaseConnection.from_url(
                connection_name="admin",
                database_url=admin_db_url,
                region_id="admin"
            )
            database_connections.append(admin_connection)
            
            # Connect to admin database to load other connections
            conn = await ConnectionFactory.create_connection_from_url(
                admin_db_url,
                connection_name="admin_failover_load"
            )
            
            try:
                # Query all active database connections except admin
                query = CONNECTION_REGISTRY_LOAD_NON_ADMIN
                
                rows = await conn.fetch(query)
                
                for row in rows:
                    try:
                        # Decrypt password if encrypted
                        password = row["encrypted_password"]
                        if password and is_encrypted(password):
                            password = decrypt_password(password)
                        
                        # Create connection object
                        connection = DatabaseConnection(
                            id=DatabaseConnectionId(row["id"]) if row["id"] else DatabaseConnectionId(generate_uuid7()),
                            connection_name=row["connection_name"],
                            host=row["host"],
                            port=row["port"] or 5432,
                            database_name=row["database_name"],
                            username=row["username"],
                            encrypted_password=password,
                            ssl_mode=row["ssl_mode"] or "prefer",
                            connection_type=ConnectionType(row["connection_type"]),
                            region_id=RegionId(row["region_id"]),
                            connection_options=row["connection_options"] or {},
                            pool_min_size=row["pool_min_size"] or 5,
                            pool_max_size=row["pool_max_size"] or 20,
                            pool_timeout_seconds=row["pool_timeout_seconds"] or 30,
                            pool_recycle_seconds=row["pool_recycle_seconds"] or 3600,
                            pool_pre_ping=row["pool_pre_ping"] if row["pool_pre_ping"] is not None else True,
                            is_active=row["is_active"] if row["is_active"] is not None else True,
                            is_healthy=row["is_healthy"] if row["is_healthy"] is not None else True,
                            last_health_check=row.get("last_health_check"),
                            consecutive_failures=row.get("consecutive_failures") or 0,
                            max_consecutive_failures=row.get("max_consecutive_failures") or 3,
                            metadata=row.get("metadata") or {},
                            tags=row.get("tags") or [],
                            created_at=row["created_at"] or datetime.now(timezone.utc),
                            updated_at=row["updated_at"] or datetime.now(timezone.utc),
                            deleted_at=row.get("deleted_at")
                        )
                        
                        database_connections.append(connection)
                        
                    except Exception as connection_error:
                        sync_stats["connections_failed"] += 1
                        sync_stats["errors"].append(f"Failed to load connection {row.get('connection_name', 'unknown')}: {connection_error}")
                        continue
                
            finally:
                await conn.close()
            
            # Sync all connections to Redis registry
            await redis_registry.sync_from_database(database_connections)
            sync_stats["connections_synced"] = len(database_connections)
            
            logger.info(f"Redis registry sync completed: {sync_stats['connections_synced']} connections synced, {sync_stats['connections_failed']} failed")
            return sync_stats
            
        except Exception as e:
            logger.error(f"Failed to sync Redis registry: {e}")
            raise DatabaseError(f"Redis registry sync failed: {e}")
    
    async def reload_configuration(self) -> Dict[str, Any]:
        """Hot-reload connection configurations without restart requirement."""
        try:
            logger.info("Starting configuration hot-reload...")
            reload_stats = {
                "connections_before": 0,
                "connections_after": 0,
                "added": [],
                "updated": [],
                "removed": [],
                "errors": []
            }
            
            # Get current connections
            current_connections = await self.connection_registry.list_connections()
            reload_stats["connections_before"] = len(current_connections)
            current_names = {conn.connection_name for conn in current_connections}
            
            # Load fresh configuration from database
            new_registry = InMemoryConnectionRegistry()
            await self._auto_load_database_connections(new_registry)
            new_connections = await new_registry.list_connections()
            new_names = {conn.connection_name for conn in new_connections}
            
            # Identify changes
            added_names = new_names - current_names
            removed_names = current_names - new_names
            potentially_updated = new_names & current_names
            
            # Process additions
            for conn in new_connections:
                if conn.connection_name in added_names:
                    try:
                        await self.connection_registry.register_connection(conn)
                        reload_stats["added"].append(conn.connection_name)
                        logger.info(f"Added new connection: {conn.connection_name}")
                    except Exception as e:
                        reload_stats["errors"].append(f"Failed to add {conn.connection_name}: {str(e)}")
            
            # Process updates
            for conn in new_connections:
                if conn.connection_name in potentially_updated:
                    try:
                        current_conn = await self.connection_registry.get_connection_by_name(conn.connection_name)
                        if current_conn and self._connection_changed(current_conn, conn):
                            await self.connection_registry.update_connection(conn)
                            reload_stats["updated"].append(conn.connection_name)
                            logger.info(f"Updated connection: {conn.connection_name}")
                    except Exception as e:
                        reload_stats["errors"].append(f"Failed to update {conn.connection_name}: {str(e)}")
            
            # Process removals
            for conn_name in removed_names:
                try:
                    current_conn = await self.connection_registry.get_connection_by_name(conn_name)
                    if current_conn:
                        await self.connection_registry.remove_connection(current_conn.id)
                        reload_stats["removed"].append(conn_name)
                        logger.info(f"Removed connection: {conn_name}")
                except Exception as e:
                    reload_stats["errors"].append(f"Failed to remove {conn_name}: {str(e)}")
            
            # Final stats
            final_connections = await self.connection_registry.list_connections()
            reload_stats["connections_after"] = len(final_connections)
            
            logger.info(f"Configuration reload completed: {len(reload_stats['added'])} added, "
                       f"{len(reload_stats['updated'])} updated, {len(reload_stats['removed'])} removed")
            
            return reload_stats
            
        except Exception as e:
            logger.error(f"Configuration reload failed: {e}")
            return {"error": str(e), "success": False}
    
    def _connection_changed(self, current: DatabaseConnection, new: DatabaseConnection) -> bool:
        """Check if connection configuration has changed."""
        # Compare key configuration attributes that would require reload
        return (
            current.host != new.host or
            current.port != new.port or
            current.database_name != new.database_name or
            current.username != new.username or
            current.encrypted_password != new.encrypted_password or
            current.pool_min_size != new.pool_min_size or
            current.pool_max_size != new.pool_max_size or
            current.pool_timeout_seconds != new.pool_timeout_seconds or
            current.ssl_mode != new.ssl_mode or
            current.is_active != new.is_active
        )
    
    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown the database service."""
        if cls._instance:
            await cls._instance.shutdown()
            cls._instance = None


# Convenience functions for easy access
@medium_performance(name="database.get_database_service")
async def get_database_service() -> DatabaseService:
    """Get database service instance."""
    return await DatabaseManager.get_instance()


@critical_performance(name="database.get_connection_pool_convenience", include_args=True)
async def get_connection_pool(connection_name: str) -> ConnectionPool:
    """Get connection pool by name."""
    service = await get_database_service()
    return await service.get_connection_pool(connection_name)


@critical_performance(name="database.get_tenant_connection_pool_convenience", include_args=True)
async def get_tenant_connection_pool(tenant_id: str) -> ConnectionPool:
    """Get connection pool for tenant."""
    service = await get_database_service()
    return await service.get_tenant_connection_pool(tenant_id)