"""Redis-backed ConnectionRegistry implementation for distributed deployments.

This module provides a distributed connection registry using Redis as the backend,
enabling connection management across multiple service instances.
"""

import json
import logging
from typing import Dict, Optional, List, Set
from datetime import datetime
import asyncio

from ..entities.protocols import ConnectionRegistry
from ..entities.database_connection import DatabaseConnection
from ....core.value_objects.identifiers import DatabaseConnectionId, RegionId
from ....config.constants import ConnectionType, HealthStatus
from ....core.exceptions.database import (
    ConnectionNotFoundError,
    EntityAlreadyExistsError,
    DatabaseConfigurationError
)
from ...cache.entities.protocols import Cache

logger = logging.getLogger(__name__)


class RedisConnectionRegistry(ConnectionRegistry):
    """Redis-backed implementation of ConnectionRegistry for distributed deployments."""
    
    def __init__(self, cache: Cache, key_prefix: str = "neo:db:connections"):
        """Initialize Redis connection registry.
        
        Args:
            cache: Redis cache instance for storage
            key_prefix: Prefix for all Redis keys
        """
        self._cache = cache
        self._key_prefix = key_prefix
        self._lock_key = f"{key_prefix}:locks"
        self._lock_timeout = 30  # seconds
        
        # Cache keys
        self._connections_key = f"{key_prefix}:all"
        self._names_key = f"{key_prefix}:names"
        self._types_key = f"{key_prefix}:types"
        self._regions_key = f"{key_prefix}:regions"
        self._health_key = f"{key_prefix}:health"
        self._stats_key = f"{key_prefix}:stats"
    
    async def initialize(self) -> None:
        """Initialize the Redis connection registry."""
        try:
            # Ensure Redis connection is healthy
            if not await self._cache.health_check():
                raise DatabaseConfigurationError("Redis cache health check failed")
            
            # Initialize indexes if they don't exist
            await self._ensure_indexes()
            
            logger.info("Redis connection registry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection registry: {e}")
            raise DatabaseConfigurationError(f"Registry initialization failed: {e}")
    
    async def _ensure_indexes(self) -> None:
        """Ensure Redis indexes exist."""
        # Initialize hash maps if they don't exist
        for key in [self._names_key, self._types_key, self._regions_key]:
            if not await self._cache.exists(key):
                # Create empty hash to ensure it exists
                await self._cache.set(f"{key}:initialized", "true", ttl=1)
    
    async def _get_distributed_lock(self, operation: str) -> str:
        """Get distributed lock key for operation."""
        return f"{self._lock_key}:{operation}"
    
    async def _serialize_connection(self, connection: DatabaseConnection) -> str:
        """Serialize connection to JSON string."""
        try:
            data = {
                "id": str(connection.id),
                "connection_name": connection.connection_name,
                "host": connection.host,
                "port": connection.port,
                "database_name": connection.database_name,
                "username": connection.username,
                "encrypted_password": connection.encrypted_password,
                "ssl_mode": connection.ssl_mode,
                "connection_type": connection.connection_type.value,
                "region_id": str(connection.region_id),
                "is_active": connection.is_active,
                "is_healthy": connection.is_healthy,
                "health_status": connection.health_status.value if connection.health_status else None,
                "consecutive_failures": connection.consecutive_failures,
                "max_consecutive_failures": connection.max_consecutive_failures,
                "last_health_check": connection.last_health_check.isoformat() if connection.last_health_check else None,
                "is_deleted": connection.is_deleted,
                "created_at": connection.created_at.isoformat(),
                "updated_at": connection.updated_at.isoformat() if connection.updated_at else None,
            }
            return json.dumps(data)
        except Exception as e:
            logger.error(f"Failed to serialize connection {connection.connection_name}: {e}")
            raise DatabaseConfigurationError(f"Connection serialization failed: {e}")
    
    async def _deserialize_connection(self, data: str) -> DatabaseConnection:
        """Deserialize connection from JSON string."""
        try:
            conn_data = json.loads(data)
            
            # Convert string values back to proper types
            connection_type = ConnectionType(conn_data["connection_type"])
            health_status = HealthStatus(conn_data["health_status"]) if conn_data.get("health_status") else None
            
            # Parse dates
            created_at = datetime.fromisoformat(conn_data["created_at"])
            updated_at = datetime.fromisoformat(conn_data["updated_at"]) if conn_data.get("updated_at") else None
            last_health_check = datetime.fromisoformat(conn_data["last_health_check"]) if conn_data.get("last_health_check") else None
            
            # Create DatabaseConnection instance
            connection = DatabaseConnection(
                id=DatabaseConnectionId(conn_data["id"]),
                connection_name=conn_data["connection_name"],
                host=conn_data["host"],
                port=conn_data["port"],
                database_name=conn_data["database_name"],
                username=conn_data["username"],
                encrypted_password=conn_data["encrypted_password"],
                ssl_mode=conn_data["ssl_mode"],
                connection_type=connection_type,
                region_id=RegionId(conn_data["region_id"]),
                is_active=conn_data["is_active"],
                is_healthy=conn_data["is_healthy"],
                consecutive_failures=conn_data["consecutive_failures"],
                max_consecutive_failures=conn_data["max_consecutive_failures"],
                is_deleted=conn_data["is_deleted"],
                created_at=created_at,
                updated_at=updated_at
            )
            
            # Set additional properties
            if health_status:
                connection.health_status = health_status
            if last_health_check:
                connection.last_health_check = last_health_check
                
            return connection
            
        except Exception as e:
            logger.error(f"Failed to deserialize connection data: {e}")
            raise DatabaseConfigurationError(f"Connection deserialization failed: {e}")
    
    async def register_connection(self, connection: DatabaseConnection) -> None:
        """Register a new database connection in Redis."""
        lock_key = await self._get_distributed_lock("register")
        
        # Use Redis transaction for atomic operation
        async with self._cache.transaction() as tx:
            connection_id = str(connection.id)
            
            # Check if connection already exists
            existing_conn = await self._cache.get(f"{self._connections_key}:{connection_id}")
            if existing_conn:
                raise EntityAlreadyExistsError("DatabaseConnection", connection_id)
            
            # Check if name is already taken
            existing_name = await self._cache.get(f"{self._names_key}:{connection.connection_name}")
            if existing_name and existing_name != connection_id:
                raise EntityAlreadyExistsError(
                    "DatabaseConnection", 
                    f"name '{connection.connection_name}'"
                )
            
            # Serialize connection
            conn_data = await self._serialize_connection(connection)
            
            # Store in Redis with atomic operations
            await tx.set(f"{self._connections_key}:{connection_id}", conn_data)
            await tx.set(f"{self._names_key}:{connection.connection_name}", connection_id)
            
            # Update type index
            await tx.set(f"{self._types_key}:{connection.connection_type.value}:{connection_id}", "1")
            
            # Update region index  
            await tx.set(f"{self._regions_key}:{connection.region_id}:{connection_id}", "1")
            
            # Update health status
            await tx.set(f"{self._health_key}:{connection_id}", 
                        f"{connection.is_healthy}:{connection.consecutive_failures}")
        
        logger.info(f"Registered connection in Redis: {connection.connection_name} ({connection_id})")
    
    async def get_connection(self, connection_id: DatabaseConnectionId) -> Optional[DatabaseConnection]:
        """Get a connection by ID from Redis."""
        try:
            connection_id_str = str(connection_id)
            conn_data = await self._cache.get(f"{self._connections_key}:{connection_id_str}")
            
            if not conn_data:
                return None
            
            connection = await self._deserialize_connection(conn_data)
            
            if connection.is_deleted:
                return None
                
            return connection
            
        except Exception as e:
            logger.error(f"Failed to get connection {connection_id}: {e}")
            return None
    
    async def get_connection_by_name(self, connection_name: str) -> Optional[DatabaseConnection]:
        """Get a connection by name from Redis."""
        try:
            # Get connection ID from name index
            connection_id = await self._cache.get(f"{self._names_key}:{connection_name}")
            
            if not connection_id:
                return None
            
            # Get connection by ID
            return await self.get_connection(DatabaseConnectionId(connection_id))
            
        except Exception as e:
            logger.error(f"Failed to get connection by name {connection_name}: {e}")
            return None
    
    async def list_connections(self,
                              connection_type: Optional[ConnectionType] = None,
                              region_id: Optional[RegionId] = None,
                              active_only: bool = True) -> List[DatabaseConnection]:
        """List connections with optional filtering from Redis."""
        try:
            connections = []
            
            if connection_type and region_id:
                # Get intersection of type and region
                type_pattern = f"{self._types_key}:{connection_type.value}:*"
                region_pattern = f"{self._regions_key}:{region_id}:*"
                
                type_keys = await self._cache.keys(type_pattern)
                region_keys = await self._cache.keys(region_pattern)
                
                # Extract connection IDs and find intersection
                type_ids = {key.split(':')[-1] for key in type_keys}
                region_ids = {key.split(':')[-1] for key in region_keys}
                connection_ids = type_ids.intersection(region_ids)
                
            elif connection_type:
                # Get connections by type
                type_keys = await self._cache.keys(f"{self._types_key}:{connection_type.value}:*")
                connection_ids = {key.split(':')[-1] for key in type_keys}
                
            elif region_id:
                # Get connections by region
                region_keys = await self._cache.keys(f"{self._regions_key}:{region_id}:*")
                connection_ids = {key.split(':')[-1] for key in region_keys}
                
            else:
                # Get all connections
                all_keys = await self._cache.keys(f"{self._connections_key}:*")
                connection_ids = {key.split(':')[-1] for key in all_keys}
            
            # Load all matching connections
            for conn_id in connection_ids:
                connection = await self.get_connection(DatabaseConnectionId(conn_id))
                
                if connection and not connection.is_deleted:
                    if not active_only or connection.is_active:
                        connections.append(connection)
            
            # Sort by connection name for consistent ordering
            connections.sort(key=lambda c: c.connection_name)
            return connections
            
        except Exception as e:
            logger.error(f"Failed to list connections: {e}")
            return []
    
    async def update_connection(self, connection: DatabaseConnection) -> None:
        """Update an existing connection in Redis."""
        lock_key = await self._get_distributed_lock("update")
        
        async with self._cache.transaction() as tx:
            connection_id = str(connection.id)
            
            # Check if connection exists
            existing_data = await self._cache.get(f"{self._connections_key}:{connection_id}")
            if not existing_data:
                raise ConnectionNotFoundError(connection.connection_name)
            
            # Get old connection for comparison
            old_connection = await self._deserialize_connection(existing_data)
            
            # Update name index if name changed
            if old_connection.connection_name != connection.connection_name:
                await tx.delete(f"{self._names_key}:{old_connection.connection_name}")
                await tx.set(f"{self._names_key}:{connection.connection_name}", connection_id)
            
            # Update type index if type changed
            if old_connection.connection_type != connection.connection_type:
                await tx.delete(f"{self._types_key}:{old_connection.connection_type.value}:{connection_id}")
                await tx.set(f"{self._types_key}:{connection.connection_type.value}:{connection_id}", "1")
            
            # Update region index if region changed
            if old_connection.region_id != connection.region_id:
                await tx.delete(f"{self._regions_key}:{old_connection.region_id}:{connection_id}")
                await tx.set(f"{self._regions_key}:{connection.region_id}:{connection_id}", "1")
            
            # Update connection data
            connection.updated_at = datetime.utcnow()
            conn_data = await self._serialize_connection(connection)
            await tx.set(f"{self._connections_key}:{connection_id}", conn_data)
            
            # Update health status
            await tx.set(f"{self._health_key}:{connection_id}",
                        f"{connection.is_healthy}:{connection.consecutive_failures}")
        
        logger.info(f"Updated connection in Redis: {connection.connection_name} ({connection_id})")
    
    async def remove_connection(self, connection_id: DatabaseConnectionId) -> None:
        """Remove a connection from Redis registry."""
        lock_key = await self._get_distributed_lock("remove")
        
        async with self._cache.transaction() as tx:
            connection_id_str = str(connection_id)
            
            # Get connection to remove
            connection = await self.get_connection(connection_id)
            if not connection:
                raise ConnectionNotFoundError(str(connection_id))
            
            # Remove from all indexes
            await tx.delete(f"{self._connections_key}:{connection_id_str}")
            await tx.delete(f"{self._names_key}:{connection.connection_name}")
            await tx.delete(f"{self._types_key}:{connection.connection_type.value}:{connection_id_str}")
            await tx.delete(f"{self._regions_key}:{connection.region_id}:{connection_id_str}")
            await tx.delete(f"{self._health_key}:{connection_id_str}")
        
        logger.info(f"Removed connection from Redis: {connection.connection_name} ({connection_id_str})")
    
    async def get_healthy_connections(self, 
                                    connection_type: Optional[ConnectionType] = None,
                                    region_id: Optional[RegionId] = None) -> List[DatabaseConnection]:
        """Get all healthy connections from Redis."""
        connections = await self.list_connections(connection_type, region_id, active_only=True)
        
        # Filter to only healthy connections
        healthy_connections = [
            conn for conn in connections 
            if conn.is_healthy and conn.health_status == HealthStatus.HEALTHY
        ]
        
        return healthy_connections
    
    async def get_connections_by_region(self, region_id: RegionId) -> List[DatabaseConnection]:
        """Get all connections in a specific region from Redis."""
        return await self.list_connections(region_id=region_id, active_only=False)
    
    async def get_connections_by_type(self, connection_type: ConnectionType) -> List[DatabaseConnection]:
        """Get all connections of a specific type from Redis."""
        return await self.list_connections(connection_type=connection_type, active_only=False)
    
    async def get_primary_connections(self) -> List[DatabaseConnection]:
        """Get all primary connections from Redis."""
        return await self.get_connections_by_type(ConnectionType.PRIMARY)
    
    async def get_replica_connections(self) -> List[DatabaseConnection]:
        """Get all replica connections from Redis."""
        return await self.get_connections_by_type(ConnectionType.REPLICA)
    
    async def get_analytics_connections(self) -> List[DatabaseConnection]:
        """Get all analytics connections from Redis."""
        return await self.get_connections_by_type(ConnectionType.ANALYTICS)
    
    async def update_health_status(self, 
                                  connection_id: DatabaseConnectionId,
                                  is_healthy: bool,
                                  consecutive_failures: int = 0) -> None:
        """Update health status for a connection in Redis."""
        try:
            connection = await self.get_connection(connection_id)
            if connection:
                connection.is_healthy = is_healthy
                connection.consecutive_failures = consecutive_failures
                connection.last_health_check = datetime.utcnow()
                
                if is_healthy:
                    connection.reset_failure_count()
                else:
                    connection.mark_unhealthy("Health check failed")
                
                # Update in Redis
                await self.update_connection(connection)
                
                # Update health index
                await self._cache.set(f"{self._health_key}:{str(connection_id)}",
                                    f"{is_healthy}:{consecutive_failures}")
                
        except Exception as e:
            logger.error(f"Failed to update health status for {connection_id}: {e}")
    
    async def get_registry_stats(self) -> Dict[str, int]:
        """Get statistics about the Redis connection registry."""
        try:
            # Get all connection IDs
            all_keys = await self._cache.keys(f"{self._connections_key}:*")
            total_connections = len(all_keys)
            
            # Count active and healthy connections
            active_connections = 0
            healthy_connections = 0
            
            for key in all_keys:
                conn_id = key.split(':')[-1]
                connection = await self.get_connection(DatabaseConnectionId(conn_id))
                
                if connection and not connection.is_deleted:
                    if connection.is_active:
                        active_connections += 1
                    if connection.is_healthy:
                        healthy_connections += 1
            
            # Count by type
            type_counts = {}
            for conn_type in ConnectionType:
                type_keys = await self._cache.keys(f"{self._types_key}:{conn_type.value}:*")
                type_counts[conn_type.value] = len(type_keys)
            
            return {
                "total_connections": total_connections,
                "active_connections": active_connections,
                "healthy_connections": healthy_connections,
                "deleted_connections": total_connections - active_connections,
                **type_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get registry stats: {e}")
            return {}
    
    async def clear_registry(self) -> None:
        """Clear all connections from the Redis registry (for testing)."""
        try:
            # Delete all connection-related keys
            patterns = [
                f"{self._connections_key}:*",
                f"{self._names_key}:*", 
                f"{self._types_key}:*",
                f"{self._regions_key}:*",
                f"{self._health_key}:*"
            ]
            
            for pattern in patterns:
                keys = await self._cache.keys(pattern)
                if keys:
                    await self._cache.delete_many(keys)
            
            logger.warning("Cleared all connections from Redis registry")
            
        except Exception as e:
            logger.error(f"Failed to clear Redis registry: {e}")
    
    async def get_all_connections(self) -> List[DatabaseConnection]:
        """Get all registered connections from Redis."""
        return await self.list_connections(active_only=False)
    
    async def list_connections(self, active_only: bool = False) -> List[DatabaseConnection]:
        """List connections with optional filtering by active status from Redis."""
        return await self.list_connections(active_only=active_only)
    
    async def sync_from_database(self, database_connections: List[DatabaseConnection]) -> None:
        """Sync Redis registry with database connections.
        
        This method is useful for initial loading or periodic synchronization
        between the database source of truth and the Redis registry.
        """
        try:
            logger.info(f"Starting Redis registry sync with {len(database_connections)} connections")
            
            # Clear existing registry
            await self.clear_registry()
            
            # Register all connections
            for connection in database_connections:
                try:
                    await self.register_connection(connection)
                except Exception as e:
                    logger.error(f"Failed to sync connection {connection.connection_name}: {e}")
            
            logger.info(f"Completed Redis registry sync with {len(database_connections)} connections")
            
        except Exception as e:
            logger.error(f"Failed to sync Redis registry from database: {e}")
            raise DatabaseConfigurationError(f"Registry sync failed: {e}")
    
    async def get_connection_keys(self, pattern: str = "*") -> List[str]:
        """Get connection keys matching pattern for debugging."""
        try:
            return await self._cache.keys(f"{self._connections_key}:{pattern}")
        except Exception as e:
            logger.error(f"Failed to get connection keys: {e}")
            return []